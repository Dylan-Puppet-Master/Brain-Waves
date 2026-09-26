"""`SheetsWorkbook` against a stand-in for gspread's HTTP client.

Every call here is a round trip to Google, so what is checked is how many there are and
what each one asks for, against the signatures gspread's `HTTPClient` really has.
"""

from inspect import signature

import pytest
from gspread.http_client import HTTPClient

from brainwaves.sheets.source import LoadError, SheetsWorkbook


class FakeHttp:
    """Answers like the Sheets API, and writes down every call."""

    def __init__(self, tabs=("Sheet1",)):
        self.calls: list[tuple[str, dict]] = []
        self.tabs = {title: index for index, title in enumerate(tabs)}

    def _record(self, name, *args, **kwargs):
        signature(getattr(HTTPClient, name)).bind(None, *args, **kwargs)
        self.calls.append((name, kwargs or {"args": args}))

    def fetch_sheet_metadata(self, id, params=None):
        self._record("fetch_sheet_metadata", id, params=params)
        return {
            "properties": {"title": "Cabin Act Sorting - S2W1"},
            "sheets": [
                {
                    "properties": {
                        "sheetId": sheet_id,
                        "title": title,
                        "gridProperties": {"rowCount": 1000, "columnCount": 26},
                    }
                }
                for title, sheet_id in self.tabs.items()
            ],
        }

    def values_batch_get(self, id, ranges, params=None):
        self._record("values_batch_get", id, ranges)
        return {"valueRanges": [{"values": [["x"]]} for _ in ranges]}

    def values_batch_update(self, id, body=None):
        self._record("values_batch_update", id, body=body)
        return {}

    def values_batch_clear(self, id, params=None, body=None):
        self._record("values_batch_clear", id, body=body)
        return {}

    def batch_update(self, id, body):
        self._record("batch_update", id, body)
        replies = []
        for request in body["requests"]:
            if "addSheet" in request:
                title = request["addSheet"]["properties"]["title"]
                self.tabs[title] = len(self.tabs) + 100
                replies.append(
                    {"addSheet": {"properties": {"sheetId": self.tabs[title], "title": title}}}
                )
            else:
                replies.append({})
        return {"replies": replies}

    def names(self):
        return [name for name, _ in self.calls]


def test_tabs_are_looked_up_once_with_a_field_mask():
    http = FakeHttp(("Board", "Roster"))
    workbook = SheetsWorkbook(http, "file")
    workbook.tab_id("Board")
    workbook.tabs()
    workbook.read_many(["Board", "Roster"])
    assert http.names() == ["fetch_sheet_metadata", "values_batch_get"]
    assert "fields" in http.calls[0][1]["params"]
    assert workbook.title == "Cabin Act Sorting - S2W1"


def test_a_missing_tab_is_named_before_google_is_asked():
    http = FakeHttp(("Board",))
    with pytest.raises(LoadError, match="Roster"):
        SheetsWorkbook(http, "file").read_many(["Board", "Roster"])
    assert "values_batch_get" not in http.names()


def test_a_read_once_spreadsheet_is_not_listed_first():
    http = FakeHttp(("Skills",))
    SheetsWorkbook(http, "file").read_once("Skills")
    assert http.names() == ["values_batch_get"]


def test_writes_to_several_tabs_are_one_request():
    http = FakeHttp(("Board", "Support Requests"))
    workbook = SheetsWorkbook(http, "file")
    workbook.write_batch(
        [
            ("Board", "C4", [["Canoe"]]),
            ("Support Requests", "A1", [["=not a formula"]]),
            ("Board", "E4", []),
        ]
    )
    assert http.names() == ["values_batch_update"]
    data = http.calls[0][1]["body"]["data"]
    assert [d["range"] for d in data] == ["'Board'!C4", "'Support Requests'!A1"]
    assert data[1]["values"] == [["'=not a formula"]]


def test_a_new_spreadsheet_gets_its_tabs_in_one_request():
    http = FakeHttp(("Sheet1",))
    workbook = SheetsWorkbook(http, "file")
    workbook.ensure_tabs(["Board", "Roster", "Locations"], rename_first=True)
    assert http.names() == ["fetch_sheet_metadata", "batch_update"]
    requests = http.calls[1][1]["args"][1]["requests"]
    assert "updateSheetProperties" in requests[0]
    assert sum("addSheet" in r for r in requests) == 2
    assert set(workbook.tabs()) == {"Board", "Roster", "Locations"}
    assert workbook.tab_id("Board") == 0
    assert http.names() == ["fetch_sheet_metadata", "batch_update"]  # nothing fetched again


def test_adding_a_tab_never_renames_the_one_that_is_there():
    http = FakeHttp(("Board",))
    workbook = SheetsWorkbook(http, "file")
    workbook.clear("Support Requests")
    requests = http.calls[-1][1]["args"][1]["requests"]
    assert [next(iter(r)) for r in requests] == ["addSheet"]
    assert set(workbook.tabs()) == {"Board", "Support Requests"}


def test_clearing_a_tab_that_is_there_is_one_request():
    http = FakeHttp(("Roster",))
    workbook = SheetsWorkbook(http, "file")
    workbook.tabs()
    workbook.clear("Roster")
    assert http.names() == ["fetch_sheet_metadata", "values_batch_clear"]


def test_a_size_passed_in_is_not_fetched_again():
    http = FakeHttp(("Board",))
    workbook = SheetsWorkbook(http, "file")
    workbook.clear_beyond("Board", 10, 10, size=(20, 20))
    assert http.names() == ["values_batch_clear"]


def test_a_board_formatting_goes_in_one_batch():
    from brainwaves.defaults import DEFAULT_CABINS
    from brainwaves.model import Cabin, Week, WeekId, sort_cabins
    from brainwaves.sheets.style import board_requests

    week = Week(WeekId(2, 1), cabins=sort_cabins(Cabin(name) for name in DEFAULT_CABINS))
    http = FakeHttp(("Board",))
    SheetsWorkbook(http, "file").apply(board_requests(week, 0, "Locations", size=(1000, 26)))
    assert http.names() == ["batch_update"]


class CountingDrive:
    def __init__(self, found):
        self.found = found
        self.listed = 0
        self.trashed: set[str] = set()

    def week_sheets(self, folder_id):
        self.listed += 1
        return {week: item for week, item in self.found.items() if item.id not in self.trashed}

    def live_name(self, file_id):
        if file_id in self.trashed:
            return None
        return next((item.name for item in self.found.values() if item.id == file_id), "old name")


def workspace_with(found):
    from brainwaves.workspace import Workspace

    workspace = Workspace.__new__(Workspace)
    workspace.http = FakeHttp(("Board",))
    workspace.drive = CountingDrive(found)
    workspace._weeks = {}
    workspace.staff = None
    workspace.read = lambda workbook, week_id, report=None: (workbook.id, week_id)
    return workspace


def test_a_week_opened_again_does_not_list_the_folder_again():
    from brainwaves.google.drive import DriveItem
    from brainwaves.model import WeekId

    week = WeekId(2, 1)
    workspace = workspace_with({week: DriveItem("file-1", "Cabin Act Sorting - S2W1", False)})
    assert workspace.open_week("folder", week) == ("file-1", week)
    assert workspace.open_week("folder", week) == ("file-1", week)
    assert workspace.drive.listed == 1


def test_a_sheet_renamed_to_another_week_is_looked_for_again():
    from brainwaves.google.drive import DriveItem
    from brainwaves.model import WeekId

    week = WeekId(2, 2)
    workspace = workspace_with({})
    # Remembered as S2W2, but the file now calls itself S2W1.
    workspace._weeks["folder"] = {week: DriveItem("file-1", "old name", False)}
    assert workspace.open_week("folder", week) is None
    assert workspace.drive.listed == 1


def test_a_sheet_in_the_trash_is_not_opened_again():
    """Sheets still opens a trashed spreadsheet, so Drive has to be asked."""
    from brainwaves.google.drive import DriveItem
    from brainwaves.model import WeekId

    week = WeekId(2, 1)
    workspace = workspace_with({week: DriveItem("file-1", "Cabin Act Sorting - S2W1", False)})
    assert workspace.open_week("folder", week) == ("file-1", week)
    workspace.drive.trashed.add("file-1")
    assert workspace.open_week("folder", week) is None


def test_the_staff_lists_are_one_request_a_document():
    from brainwaves.config import Config

    workspace = workspace_with({})
    workspace.config = Config(skills_sheet="skills", categories_sheet="categories")
    assert workspace.load_staff() is True
    assert workspace.staff is not None
    assert workspace.http.names() == ["values_batch_get", "values_batch_get"]


def test_staff_lists_that_cannot_be_read_are_tried_again_later():
    from brainwaves.config import Config

    workspace = workspace_with({})
    workspace.config = Config(skills_sheet="skills")

    def refuse(*args, **kwargs):
        raise ValueError("no such spreadsheet")

    workspace.http.values_batch_get = refuse
    assert workspace.load_staff() is False
    assert workspace.staff is None
