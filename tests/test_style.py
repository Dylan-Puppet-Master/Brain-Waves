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


def test_the_window_calls_google_the_way_google_is_declared():
    """Bind what `app.main` passes against the real signatures.

    Two releases in a row shipped a call the other side did not accept, because the
    window's jobs only run against Google and so never ran in a test. Binding the
    signatures is offline and catches exactly that.
    """
    from inspect import signature

    from brainwaves.model import WeekId
    from brainwaves.workspace import Workspace, write_template

    signature(Workspace.create_week).bind(None, "folder-id", WeekId(2, 1), None, report=print)
    signature(Workspace.read).bind(None, None, WeekId(2, 1))
    signature(Workspace.read_board).bind(None, None)
    signature(Workspace.weeks).bind(None, "folder-id")
    signature(Workspace.open).bind(None, "file-id", WeekId(2, 1))
    signature(Workspace.staff_names).bind(None)
    signature(write_template).bind(None, None, (), report=print)


def test_the_window_calls_the_store_the_way_the_store_is_declared():
    from inspect import signature

    from brainwaves.model import CabinAct
    from brainwaves.store import BoardStore

    signature(BoardStore.save_card).bind(None, "M1", 0, CabinAct())
    signature(BoardStore.swap).bind(None, "M1", 0, 3)
    signature(BoardStore.set_subtitle).bind(None, 3, "Pizza Day")
    signature(BoardStore.set_cabins).bind(None, ())
    signature(BoardStore.add_overflow_column).bind(None)
    signature(BoardStore.add_comment).bind(None, "card-id", "text")
    signature(BoardStore.reply).bind(None, "comment-id", "text")
    signature(BoardStore.resolve).bind(None, "comment-id")
    signature(BoardStore.poll).bind(None)
    signature(BoardStore.reload).bind(None)
    signature(BoardStore.reload_reference).bind(None)
    signature(BoardStore.flush).bind(None)
    signature(BoardStore.load_staff).bind(None)


def test_nothing_is_merged_across_the_frozen_edge(requests):
    """Google Sheets refuses to merge frozen cells with unfrozen ones.

    Creating a week failed on exactly this, so the freeze line is read back out of the
    batch and every merge in it is checked against it.
    """
    frozen = next(
        request["updateSheetProperties"]["properties"]["gridProperties"]
        for request in requests
        if "updateSheetProperties" in request
    )
    rows, columns = frozen["frozenRowCount"], frozen["frozenColumnCount"]
    for request in requests:
        if "mergeCells" not in request:
            continue
        span = request["mergeCells"]["range"]
        assert not span["startRowIndex"] < rows < span["endRowIndex"], span
        assert not span["startColumnIndex"] < columns < span["endColumnIndex"], span


def test_no_merge_overlaps_another(requests):
    """Sheets refuses a merge that crosses one already there."""
    seen: list[tuple[int, int, int, int]] = []
    for request in requests:
        if "mergeCells" not in request:
            continue
        span = request["mergeCells"]["range"]
        box = (
            span["startRowIndex"],
            span["endRowIndex"],
            span["startColumnIndex"],
            span["endColumnIndex"],
        )
        for other in seen:
            rows_overlap = box[0] < other[1] and other[0] < box[1]
            columns_overlap = box[2] < other[3] and other[2] < box[3]
            assert not (rows_overlap and columns_overlap), (box, other)
        seen.append(box)
