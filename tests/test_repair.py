"""Opening a week sheet that has lost a tab: what is kept, what is put back."""

import pytest

from brainwaves.defaults import DEFAULT_LOCATIONS
from brainwaves.model import Cabin, Week
from brainwaves.sheets import week as week_sheet
from brainwaves.sheets.source import LoadError
from brainwaves.workspace import rebuild_tabs, write_template
from tests.conftest import WEEK_ID
from tests.fakes import FakeWorkbook


def sheet_for(tmp_path, week, locations=("Hot Rocks", "Low Ropes 1")) -> FakeWorkbook:
    workbook = FakeWorkbook(tmp_path)
    write_template(workbook, week, locations)
    return workbook


def drop(tmp_path, *tabs) -> None:
    for tab in tabs:
        (tmp_path / f"{tab}.csv").unlink()


def test_a_lost_roster_comes_back_from_the_board(tmp_path, week):
    workbook = sheet_for(tmp_path, week)
    drop(tmp_path, week_sheet.ROSTER_TAB)

    rebuilt = rebuild_tabs(workbook, week.id)

    assert rebuilt.week.cabins == week.cabins
    assert week_sheet.parse_roster(workbook.read(week_sheet.ROSTER_TAB)) == week.cabins


def test_the_cards_on_the_board_survive_the_rebuild(tmp_path, week):
    workbook = sheet_for(tmp_path, week)
    drop(tmp_path, week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB)

    rebuilt = rebuild_tabs(workbook, week.id)

    assert rebuilt.week.cards == week.cards


def test_a_tab_that_is_still_there_is_left_alone(tmp_path, week):
    workbook = sheet_for(tmp_path, week, locations=("Hot Rocks",))
    drop(tmp_path, week_sheet.ROSTER_TAB)
    before = workbook.read(week_sheet.LOCATIONS_TAB)

    rebuilt = rebuild_tabs(workbook, week.id)

    assert rebuilt.locations == ("Hot Rocks",)
    assert workbook.read(week_sheet.LOCATIONS_TAB) == before


def test_a_lost_locations_tab_comes_back_with_the_defaults(tmp_path, week):
    workbook = sheet_for(tmp_path, week)
    drop(tmp_path, week_sheet.LOCATIONS_TAB)

    rebuilt = rebuild_tabs(workbook, week.id)

    assert rebuilt.locations == tuple(DEFAULT_LOCATIONS)
    assert week_sheet.parse_locations(workbook.read(week_sheet.LOCATIONS_TAB)) == rebuilt.locations


def test_the_support_tab_is_rebuilt_from_the_cards(tmp_path, week):
    workbook = sheet_for(tmp_path, week)
    drop(tmp_path, week_sheet.REQUESTS_TAB, week_sheet.ROSTER_TAB)

    rebuild_tabs(workbook, week.id)

    table = workbook.read(week_sheet.REQUESTS_TAB)
    assert any("Dylan" in cell for row in table for cell in row)


def test_the_board_is_formatted_again(tmp_path, week):
    workbook = sheet_for(tmp_path, week)
    workbook.applied.clear()
    drop(tmp_path, week_sheet.ROSTER_TAB)

    rebuild_tabs(workbook, week.id)

    board = week_sheet.BOARD_TAB
    assert any(
        request.get("repeatCell", {}).get("range", {}).get("sheetId") == workbook.tab_id(board)
        for request in workbook.applied
    )


def test_cabins_out_of_village_order_are_laid_out_again(tmp_path):
    jumbled = Week(WEEK_ID, cabins=(Cabin("P1", "Robyn"), Cabin("M1", "Jana")))
    workbook = FakeWorkbook(tmp_path)
    write_template(workbook, jumbled, ("Hot Rocks",))
    drop(tmp_path, week_sheet.ROSTER_TAB)

    rebuilt = rebuild_tabs(workbook, WEEK_ID)

    assert [c.name for c in rebuilt.week.cabins] == ["M1", "P1"]
    board = workbook.read(week_sheet.BOARD_TAB)
    assert week_sheet.parse_board_cabins(board)[0].name == "M1"


def test_a_board_laid_out_some_other_way_is_not_rebuilt_over(tmp_path, week):
    workbook = sheet_for(tmp_path, week)
    drop(tmp_path, week_sheet.ROSTER_TAB)
    workbook.write(week_sheet.BOARD_TAB, [["Whose turn"]], "B4")

    with pytest.raises(LoadError) as raised:
        rebuild_tabs(workbook, week.id)

    assert "Activity" in str(raised.value)


def test_a_board_with_no_cabins_is_not_rebuilt_over(tmp_path, week):
    workbook = sheet_for(tmp_path, week)
    drop(tmp_path, week_sheet.ROSTER_TAB)
    workbook.clear(week_sheet.BOARD_TAB)

    with pytest.raises(LoadError) as raised:
        rebuild_tabs(workbook, week.id)

    assert "no cabins" in str(raised.value)
