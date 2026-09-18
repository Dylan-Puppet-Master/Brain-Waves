"""The Sheets API refuses a malformed request, and it refuses the whole batch with it.

These checks run offline against what the API documents about itself, because the cheapest
place to find a bad request is here rather than halfway through making someone's week.
"""

import pytest

from brainwaves.model import Cabin, Week, WeekId, sort_cabins
from brainwaves.sheets import layout
from brainwaves.sheets.style import board_requests
from brainwaves.sheets.week import LOCATIONS_TAB

# Sheets requests that replace part of an object need a mask saying which part, and fail
# with "At least one field must be listed in 'fields'" without one.
NEEDS_FIELDS = {
    "updateSheetProperties",
    "updateSpreadsheetProperties",
    "updateDimensionProperties",
    "updateCells",
    "repeatCell",
    "updateNamedRange",
    "updateProtectedRange",
    "updateEmbeddedObjectPosition",
    "updateFilterView",
    "updateSlicerSpec",
    "updateDeveloperMetadata",
}

BOARD = 0


@pytest.fixture
def requests():
    cabins = sort_cabins(Cabin(name) for name in ("M1", "M2", "P1", "O1", "C1"))
    week = Week(WeekId(2, 1), cabins=cabins)
    return board_requests(week, BOARD, LOCATIONS_TAB, new_sheet=True, size=(1000, 26))


def test_every_request_names_exactly_one_operation(requests):
    assert requests
    assert all(len(request) == 1 for request in requests)


def test_every_request_that_replaces_part_of_an_object_says_which_part(requests):
    missing = [
        kind
        for request in requests
        for kind, body in request.items()
        if kind in NEEDS_FIELDS and not body.get("fields")
    ]
    assert missing == []


def test_the_grid_is_grown_and_never_trimmed(requests):
    grid = next(
        request["updateSheetProperties"]["properties"]["gridProperties"]
        for request in requests
        if "updateSheetProperties" in request
    )
    assert grid["rowCount"] >= 1000  # the tab already had that many
    assert grid["columnCount"] >= 1 + 8 * layout.CARD_COLUMNS
    assert grid["frozenRowCount"] == layout.FIRST_CARD_ROW


def test_a_rewrite_leaves_the_conditional_formats_alone(requests):
    cabins = sort_cabins(Cabin(name) for name in ("M1", "M2"))
    week = Week(WeekId(2, 1), cabins=cabins)
    rewrite = board_requests(week, BOARD, LOCATIONS_TAB, size=(200, 60))
    assert any("addConditionalFormatRule" in request for request in requests)
    assert not any("addConditionalFormatRule" in request for request in rewrite)


def test_every_range_stays_inside_the_board(requests):
    cabins = 5
    rows, columns = layout.grid_size(cabins, 8)
    for request in requests:
        for body in request.values():
            for grid in _ranges(body):
                assert grid.get("endRowIndex", rows) <= max(rows, 1000)
                assert grid.get("endColumnIndex", columns) <= columns
                assert grid.get("startRowIndex", 0) >= 0
                assert grid.get("startColumnIndex", 0) >= 0


def _ranges(body):
    if isinstance(body, dict):
        if "sheetId" in body and "startRowIndex" in body:
            yield body
        for value in body.values():
            yield from _ranges(value)
    elif isinstance(body, list):
        for item in body:
            yield from _ranges(item)


def test_making_a_week_formats_every_tab_it_makes(tmp_path, week):
    from brainwaves.workspace import write_template
    from tests.fakes import TAB_IDS, FakeWorkbook

    workbook = FakeWorkbook(tmp_path)
    write_template(workbook, week, ("Hot Rocks",))
    aimed_at = {
        body["range"]["sheetId"] if "range" in body else body["properties"]["sheetId"]
        for request in workbook.applied
        for body in request.values()
        if isinstance(body, dict) and ("range" in body or "properties" in body)
    }
    assert aimed_at >= set(TAB_IDS.values())


def test_making_a_week_sends_no_request_without_its_field_mask(tmp_path, week):
    from brainwaves.workspace import write_template
    from tests.fakes import FakeWorkbook

    workbook = FakeWorkbook(tmp_path)
    write_template(workbook, week, ("Hot Rocks",))
    assert workbook.applied
    missing = [
        kind
        for request in workbook.applied
        for kind, body in request.items()
        if kind in NEEDS_FIELDS and not body.get("fields")
    ]
    assert missing == []


def test_making_a_week_colours_the_risk_cells(tmp_path, week):
    from brainwaves.workspace import write_template
    from tests.fakes import FakeWorkbook

    workbook = FakeWorkbook(tmp_path)
    write_template(workbook, week, ("Hot Rocks",))
    rules = [r for r in workbook.applied if "addConditionalFormatRule" in r]
    assert len(rules) == 3  # red, yellow and green; none needs no colour


def test_making_a_week_reports_what_it_is_doing(tmp_path, week):
    from brainwaves.workspace import write_template
    from tests.fakes import FakeWorkbook

    said = []
    write_template(FakeWorkbook(tmp_path), week, ("Hot Rocks",), report=said.append)
    assert "Writing the board" in said
    assert len(said) >= 4
