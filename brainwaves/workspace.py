"""Everything Brain Waves does to Google: find week sheets, open one, make a new one.

The rest of the program works in terms of `Week` and `Comment`; this is where those meet
Drive and Sheets.
"""

from dataclasses import dataclass, replace

from brainwaves.config import Config
from brainwaves.defaults import DEFAULT_CABINS, DEFAULT_LOCATIONS
from brainwaves.google.comments import CommentStore
from brainwaves.google.drive import Drive, DriveItem
from brainwaves.model import Cabin, Week, WeekId, sort_cabins
from brainwaves.sheets import layout, style
from brainwaves.sheets import week as week_sheet
from brainwaves.sheets.source import LoadError, SheetsWorkbook, Table, trimmed
from brainwaves.sheets.staff import (
    StaffLists,
    parse_categories,
    parse_skills,
    parse_staff_names,
)
from brainwaves.sheets.support import render_support

# The tabs that can be worked out again from the board, and so put back if they go missing.
REBUILDABLE_TABS = (week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB, week_sheet.REQUESTS_TAB)

# The tabs a week is read from. The Support Requests tab is read alongside them when it is
# there, so a write can tell whether it needs rewriting at all.
WEEK_TABS = (week_sheet.BOARD_TAB, week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB)

# Every tab a week sheet has, in the order a new one is given them.
ALL_TABS = (week_sheet.BOARD_TAB, *REBUILDABLE_TABS)


class WeekExists(Exception):
    """A week sheet with that session and week is already in the folder."""


@dataclass(frozen=True)
class WeekSheet:
    """An open week: its workbook, the week it holds, and its locations.

    `support` is the Support Requests tab as it was read, trimmed, or None if it was not.
    """

    workbook: SheetsWorkbook
    week: Week
    locations: tuple[str, ...]
    support: Table | None = None

    @property
    def board_tab_id(self) -> int:
        """The numeric id of the Board tab, which comment anchors are written against."""
        return self.workbook.tab_id(week_sheet.BOARD_TAB)


class Workspace:
    """The signed-in user's Google Drive and the week sheets in it.

    Two things are kept once found, because finding them is slow and they hardly change:
    which sheet in a folder holds which week, and the staff lists. `staff` is None until
    the lists have been read.
    """

    def __init__(self, credentials, config: Config) -> None:
        import gspread

        self.config = config
        self.http = gspread.authorize(credentials).http_client
        self.drive = Drive(credentials)
        self.comments = CommentStore(credentials)
        self._weeks: dict[str, dict[WeekId, DriveItem]] = {}
        self.staff: StaffLists | None = None

    def weeks(self, folder_id: str) -> dict[WeekId, DriveItem]:
        """Which weeks already have a sheet in the folder. Always asks Drive."""
        found = self.drive.week_sheets(folder_id)
        self._weeks[folder_id] = found
        return found

    def open_week(self, folder_id: str, week_id: WeekId, report=None) -> WeekSheet | None:
        """Open the folder's sheet for a week, or None if it has none.

        The sheet found last time is tried first, which saves listing the folder. If it has
        gone, or has been renamed to some other week, the folder is listed again.
        """
        known = self._weeks.get(folder_id, {}).get(week_id)
        if known is not None:
            workbook = SheetsWorkbook(self.http, known.id)
            try:
                still_there = WeekId.parse(workbook.title) == week_id
            except Exception:  # noqa: BLE001 - moved or deleted since; look again
                still_there = False
            if still_there:
                return self.read(workbook, week_id, report=report)
        item = self.weeks(folder_id).get(week_id)
        if item is None:
            return None
        return self.open(item.id, week_id, report=report)

    def open(self, file_id: str, week_id: WeekId, report=None) -> WeekSheet:
        """Read a week sheet into a Week, rebuilding any tab it has lost."""
        return self.read(SheetsWorkbook(self.http, file_id), week_id, report=report)

    def read(self, workbook: SheetsWorkbook, week_id: WeekId, report=None) -> WeekSheet:
        """Read the Board, Roster and Locations tabs of an open workbook, in one request.

        This is also what a poll does. The roster and the locations are small next to the
        board, and asking for them in the same request costs nothing extra, where reading
        them on their own beat was a second request for the same news.

        A sheet missing anything but the board is rebuilt around what it does hold rather
        than turned away; see `rebuild_tabs`.
        """
        self._check(workbook, [week_sheet.BOARD_TAB])
        held = workbook.tabs()
        if any(tab not in held for tab in WEEK_TABS):
            return rebuild_tabs(workbook, week_id, report=report)
        return read_week(workbook, week_id)

    @staticmethod
    def _check(workbook: SheetsWorkbook, tabs) -> None:
        missing = [tab for tab in tabs if tab not in workbook.tabs()]
        if missing:
            raise LoadError(
                f"{workbook.title} is missing the {', '.join(missing)} tab. Make the week "
                "again with Start New Week, or add the tab by hand."
            )

    def create_week(
        self,
        folder_id: str,
        week_id: WeekId,
        seed: WeekSheet | None,
        report=None,
    ) -> WeekSheet:
        """Make a week sheet from the template. Raises WeekExists rather than overwrite.

        `report` is passed on to `write_template`, which names each step as it goes.
        """
        say = report or (lambda _message: None)
        say("Checking the folder")
        if week_id in self.weeks(folder_id):
            raise WeekExists(
                f"{week_id.title} is already in this folder. Open it instead, or delete it "
                "in Google Drive first."
            )
        cabins = seed.week.cabins if seed else _default_cabins()
        locations = seed.locations if seed else DEFAULT_LOCATIONS
        say(f"Creating {week_id.title}")
        made = self.drive.create_spreadsheet(week_id.title, folder_id)
        self._weeks.setdefault(folder_id, {})[week_id] = made
        workbook = SheetsWorkbook(self.http, made.id, made.name)
        week = Week(week_id, cabins=cabins)
        write_template(workbook, week, locations, report=report)
        return WeekSheet(workbook, week, tuple(locations))

    def load_staff(self) -> bool:
        """Read everything a HERO chip may hold. True if it was read.

        Read once a session. The staff documents change a few times a summer, and reading
        them is two spreadsheets' worth of requests every time a week is opened otherwise.
        A failure leaves `staff` None, so the chips stay free text and the next week opened
        tries again.
        """
        try:
            self.staff = self._read_staff()
        except Exception:  # noqa: BLE001 - HERO chips still work without the lists
            return False
        return True

    def _read_staff(self) -> StaffLists:
        names: tuple[str, ...] = ()
        skills: dict[str, int] = {}
        categories: dict[str, int] = {}
        if self.config.skills_sheet:
            table = SheetsWorkbook(self.http, self.config.skills_sheet).read_once(
                self.config.skills_tab
            )
            names, skills = parse_staff_names(table), parse_skills(table)
        if self.config.categories_sheet:
            table = SheetsWorkbook(self.http, self.config.categories_sheet).read_once(
                self.config.categories_tab
            )
            categories = parse_categories(table)
        return StaffLists(names=names, categories=categories, skills=skills)


def read_week(workbook, week_id: WeekId) -> WeekSheet:
    """Read a week from a workbook known to hold every tab in `WEEK_TABS`, in one request."""
    tabs = [*WEEK_TABS]
    if week_sheet.REQUESTS_TAB in workbook.tabs():
        tabs.append(week_sheet.REQUESTS_TAB)
    tables = workbook.read_many(tabs)
    cabins = week_sheet.parse_roster(tables[week_sheet.ROSTER_TAB])
    week = week_sheet.parse_week(week_id, tables[week_sheet.BOARD_TAB], cabins)
    locations = week_sheet.parse_locations(tables[week_sheet.LOCATIONS_TAB])
    support = tables.get(week_sheet.REQUESTS_TAB)
    return WeekSheet(
        workbook,
        week,
        locations or DEFAULT_LOCATIONS,
        None if support is None else trimmed(support),
    )


def _tab_contents(week: Week, locations, support) -> dict[str, Table]:
    """What the tabs other than the board start out holding."""
    return {
        week_sheet.ROSTER_TAB: week_sheet.render_roster(week.cabins),
        week_sheet.LOCATIONS_TAB: week_sheet.render_locations(locations),
        week_sheet.REQUESTS_TAB: support.table,
    }


def write_template(workbook: SheetsWorkbook, week: Week, locations, report=None) -> None:
    """Lay out an empty week: four tabs, written and then styled, in three requests.

    `report` is called with whatever is being done, so the window can say so. Creating a
    week is the one thing in Brain Waves slow enough to need telling.
    """
    say = report or (lambda _message: None)
    say("Naming the tabs")
    workbook.ensure_tabs(list(ALL_TABS), rename_first=True)

    say("Writing the board")
    support = render_support(week)
    contents = _tab_contents(week, locations, support)
    workbook.write_batch(
        [
            *((tab, "A1", table) for tab, table in contents.items()),
            (week_sheet.BOARD_TAB, "A1", week_sheet.render_week(week)),
        ]
    )

    say("Formatting the board")
    workbook.apply(
        [
            *style.board_requests(
                week,
                workbook.tab_id(week_sheet.BOARD_TAB),
                week_sheet.LOCATIONS_TAB,
                new_sheet=True,
                # The tab was made a moment ago by this program, so its size is known.
                size=workbook.size(week_sheet.BOARD_TAB, fresh=False),
            ),
            *_list_formats(workbook, [week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB]),
            *style.support_requests(support, workbook.tab_id(week_sheet.REQUESTS_TAB)),
        ],
        report=say,
    )


def rebuild_tabs(workbook, week_id: WeekId, report=None) -> WeekSheet:
    """Put back the tabs a week sheet has lost, keeping everything it still holds.

    The board is the only tab whose contents cannot be worked out again, so it is read and
    checked first and never overwritten - unless its cabins are out of village order, in
    which case the rows are laid out again, because from here on the roster's order is what
    says which row belongs to which cabin.

    A tab that is still there is left exactly as it is; only the missing ones are written.
    """
    say = report or (lambda _message: None)
    say("Checking the board")
    tabs = workbook.tabs()
    kept = [tab for tab in (week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB) if tab in tabs]
    tables = workbook.read_many([week_sheet.BOARD_TAB, *kept])
    board = tables[week_sheet.BOARD_TAB]
    week_sheet.check_board(board)

    if week_sheet.ROSTER_TAB in tables:
        cabins = week_sheet.parse_roster(tables[week_sheet.ROSTER_TAB])
    else:
        cabins = week_sheet.parse_board_cabins(board)
    week = week_sheet.parse_week(week_id, board, cabins)

    if week_sheet.LOCATIONS_TAB in tables:
        locations = week_sheet.parse_locations(tables[week_sheet.LOCATIONS_TAB])
    else:
        locations = ()
    locations = locations or DEFAULT_LOCATIONS

    ordered = sort_cabins(week.cabins)
    week = replace(week, cabins=ordered)

    missing = [tab for tab in REBUILDABLE_TABS if tab not in tabs]
    say(f"Adding the {', '.join(missing)} tab" + ("s" if len(missing) > 1 else ""))
    support = render_support(week)
    contents = _tab_contents(week, locations, support)
    workbook.ensure_tabs([week_sheet.BOARD_TAB, *missing])
    writes = [(tab, "A1", contents[tab]) for tab in missing]
    reordered = ordered != cabins
    if reordered:
        say("Putting the cabins in village order")
        writes.append((week_sheet.BOARD_TAB, "A1", week_sheet.render_week(week)))
    workbook.write_batch(writes)
    # The tabs were fetched a moment ago to see which were missing.
    size = workbook.size(week_sheet.BOARD_TAB, fresh=False)
    if reordered:
        rows, columns = layout.grid_size(len(week.cabins), week.columns)
        workbook.clear_beyond(week_sheet.BOARD_TAB, rows, columns, size=size)

    say("Formatting the board")
    formats = []
    if week_sheet.REQUESTS_TAB in missing:
        formats = style.support_requests(support, workbook.tab_id(week_sheet.REQUESTS_TAB))
    workbook.apply(
        [
            *style.board_requests(
                week,
                workbook.tab_id(week_sheet.BOARD_TAB),
                week_sheet.LOCATIONS_TAB,
                # A sheet that has lost a tab was rarely written by Brain Waves, so it is
                # taken to want the risk colours as well.
                new_sheet=True,
                size=size,
            ),
            *_list_formats(workbook, [tab for tab in missing if tab in LIST_TABS]),
            *formats,
        ],
        report=say,
    )
    return WeekSheet(workbook, week, tuple(locations))


# The plain list tabs, with how many columns each has and how wide they are.
LIST_TABS = {
    week_sheet.ROSTER_TAB: (3, (90, 170, 170)),
    week_sheet.LOCATIONS_TAB: (1, (260,)),
}


def _list_formats(workbook, tabs) -> list[dict]:
    requests = []
    for tab in tabs:
        columns, widths = LIST_TABS[tab]
        requests += style.list_tab_requests(workbook.tab_id(tab), columns, widths=widths)
    return requests


def _default_cabins() -> tuple[Cabin, ...]:
    return sort_cabins(Cabin(name) for name in DEFAULT_CABINS)
