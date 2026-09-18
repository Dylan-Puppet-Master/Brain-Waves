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
from brainwaves.sheets.staff import parse_staff_names
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
        missing = [tab for tab in tabs if tab not in workbook.tabs()]
        if missing:
            raise LoadError(
                f"{workbook.title} is missing the {', '.join(missing)} tab. Make the week "
                "again with Start New Week, or add the tab by hand."
            )
        tables = workbook.read_many(tabs)
        week = week_sheet.parse_week(
            week_id, tables[week_sheet.BOARD_TAB], tables[week_sheet.ROSTER_TAB]
        )
        locations = week_sheet.parse_locations(tables[week_sheet.LOCATIONS_TAB])
        return WeekSheet(workbook, week, locations or DEFAULT_LOCATIONS)

    def create_week(self, folder_id: str, week_id: WeekId, seed: WeekSheet | None) -> WeekSheet:
        """Make a week sheet from the template. Raises WeekExists rather than overwrite."""
        if week_id in self.weeks(folder_id):
            raise WeekExists(
                f"{week_id.title} is already in this folder. Open it instead, or delete it "
                "in Google Drive first."
            )
        cabins = seed.week.cabins if seed else _default_cabins()
        locations = seed.locations if seed else DEFAULT_LOCATIONS
        spreadsheet = self.client.create(week_id.title, folder_id=folder_id)
        workbook = SheetsWorkbook(spreadsheet)
        week = Week(week_id, cabins=cabins)
        write_template(workbook, week, locations)
        return WeekSheet(workbook, week, tuple(locations))

    def staff_names(self) -> tuple[str, ...]:
        """Every name on the Skills doc, for the HERO chips."""
        if not self.config.skills_sheet:
            return ()
        workbook = SheetsWorkbook(self.client.open_by_key(self.config.skills_sheet))
        return parse_staff_names(workbook.read(self.config.skills_tab))


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
