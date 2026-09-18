"""Everything Brain Waves does to Google: find week sheets, open one, make a new one.

The rest of the program works in terms of `Week` and `Comment`; this is where those meet
Drive and Sheets.
"""

from dataclasses import dataclass

from brainwaves.config import Config
from brainwaves.defaults import DEFAULT_CABINS, DEFAULT_LOCATIONS
from brainwaves.google.comments import CommentStore
from brainwaves.google.drive import Drive, DriveItem
from brainwaves.model import Cabin, Week, WeekId, sort_cabins
from brainwaves.sheets import style
from brainwaves.sheets import week as week_sheet
from brainwaves.sheets.source import LoadError, SheetsWorkbook
from brainwaves.sheets.staff import (
    StaffLists,
    parse_categories,
    parse_skills,
    parse_staff_names,
)
from brainwaves.sheets.support import render_support


class WeekExists(Exception):
    """A week sheet with that session and week is already in the folder."""


@dataclass(frozen=True)
class WeekSheet:
    """An open week: its workbook, the week it holds, and its locations."""

    workbook: SheetsWorkbook
    week: Week
    locations: tuple[str, ...]

    @property
    def board_tab_id(self) -> int:
        """The numeric id of the Board tab, which comment anchors are written against."""
        return self.workbook.tab_id(week_sheet.BOARD_TAB)


class Workspace:
    """The signed-in user's Google Drive and the week sheets in it."""

    def __init__(self, credentials, config: Config) -> None:
        import gspread

        self.config = config
        self.client = gspread.authorize(credentials)
        self.drive = Drive(credentials)
        self.comments = CommentStore(credentials)

    def weeks(self, folder_id: str) -> dict[WeekId, DriveItem]:
        """Which weeks already have a sheet in the folder."""
        return self.drive.week_sheets(folder_id)

    def open(self, file_id: str, week_id: WeekId) -> WeekSheet:
        """Read a week sheet into a Week."""
        workbook = SheetsWorkbook(self.client.open_by_key(file_id))
        return self.read(workbook, week_id)

    def read(self, workbook: SheetsWorkbook, week_id: WeekId) -> WeekSheet:
        """Read the Board, Roster and Locations tabs of an open workbook."""
        tabs = [week_sheet.BOARD_TAB, week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB]
        self._check(workbook, tabs)
        tables = workbook.read_many(tabs)
        cabins = week_sheet.parse_roster(tables[week_sheet.ROSTER_TAB])
        week = week_sheet.parse_week(week_id, tables[week_sheet.BOARD_TAB], cabins)
        locations = week_sheet.parse_locations(tables[week_sheet.LOCATIONS_TAB])
        return WeekSheet(workbook, week, locations or DEFAULT_LOCATIONS)

    def read_board(self, sheet: WeekSheet, cabins=None) -> WeekSheet:
        """Read only the Board tab, keeping the cabins and locations already in hand.

        This is what a poll does. The board is the tab people are moving cards around on;
        the roster and the locations change once a session, so re-reading them every few
        seconds would be most of the traffic for none of the news.
        """
        self._check(sheet.workbook, [week_sheet.BOARD_TAB])
        board = sheet.workbook.read(week_sheet.BOARD_TAB)
        week = week_sheet.parse_week(sheet.week.id, board, cabins or sheet.week.cabins)
        return WeekSheet(sheet.workbook, week, sheet.locations)

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
        spreadsheet = self.client.create(week_id.title, folder_id=folder_id)
        workbook = SheetsWorkbook(spreadsheet)
        week = Week(week_id, cabins=cabins)
        write_template(workbook, week, locations, report=report)
        return WeekSheet(workbook, week, tuple(locations))

    def staff_lists(self) -> StaffLists:
        """Everything a HERO chip may hold: the people, their categories, their skills."""
        names: tuple[str, ...] = ()
        skills: dict[str, int] = {}
        categories: dict[str, int] = {}
        if self.config.skills_sheet:
            workbook = SheetsWorkbook(self.client.open_by_key(self.config.skills_sheet))
            table = workbook.read(self.config.skills_tab)
            names, skills = parse_staff_names(table), parse_skills(table)
        if self.config.categories_sheet:
            workbook = SheetsWorkbook(self.client.open_by_key(self.config.categories_sheet))
            categories = parse_categories(workbook.read(self.config.categories_tab))
        return StaffLists(names=names, categories=categories, skills=skills)


def write_template(workbook: SheetsWorkbook, week: Week, locations, report=None) -> None:
    """Lay out an empty week: four tabs, written and then styled.

    `report` is called with whatever is being done, so the window can say so. Creating a
    week is the one thing in Brain Waves slow enough to need telling.
    """
    say = report or (lambda _message: None)
    say("Naming the tabs")
    workbook.spreadsheet.sheet1.update_title(week_sheet.BOARD_TAB)
    for tab in (week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB, week_sheet.REQUESTS_TAB):
        workbook.clear(tab)

    say("Writing the cabins and locations")
    support = render_support(week)
    workbook.write(week_sheet.ROSTER_TAB, week_sheet.render_roster(week.cabins))
    workbook.write(week_sheet.LOCATIONS_TAB, week_sheet.render_locations(locations))
    workbook.write(week_sheet.REQUESTS_TAB, support.table)

    say("Writing the board")
    workbook.write(week_sheet.BOARD_TAB, week_sheet.render_week(week))

    say("Formatting the board")
    workbook.apply(
        style.board_requests(
            week,
            workbook.tab_id(week_sheet.BOARD_TAB),
            week_sheet.LOCATIONS_TAB,
            new_sheet=True,
            size=workbook.size(week_sheet.BOARD_TAB),
        ),
        report=say,
    )

    say("Formatting the other tabs")
    workbook.apply(
        [
            *style.list_tab_requests(
                workbook.tab_id(week_sheet.ROSTER_TAB), 3, widths=(90, 170, 170)
            ),
            *style.list_tab_requests(workbook.tab_id(week_sheet.LOCATIONS_TAB), 1, widths=(260,)),
            *style.support_requests(support, workbook.tab_id(week_sheet.REQUESTS_TAB)),
        ]
    )


def _default_cabins() -> tuple[Cabin, ...]:
    return sort_cabins(Cabin(name) for name in DEFAULT_CABINS)
