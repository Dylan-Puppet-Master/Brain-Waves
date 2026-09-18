import pytest

from brainwaves.model import DAY_COLUMNS, Cabin, CabinAct, Risk
from brainwaves.sheets import layout
from brainwaves.sheets.source import LoadError, a1_to_index, index_to_a1
from brainwaves.sheets.week import (
    card_block,
    card_range,
    parse_locations,
    parse_roster,
    parse_week,
    render_locations,
    render_roster,
    render_week,
    subtitle_cell,
)


def test_render_then_parse_gives_the_same_week(week):
    parsed = parse_week(week.id, render_week(week), render_roster(week.cabins))
    assert parsed == week


def test_render_puts_the_title_and_day_names_where_they_belong(week):
    grid = render_week(week)
    assert grid[layout.TITLE_ROW][0] == "Cabin Act Sorting - S2W1"
    assert grid[layout.DAY_ROW][layout.column_origin(0)] == "Monday"
    assert grid[layout.DAY_ROW][layout.column_origin(DAY_COLUMNS)] == "Unplaced 1"


def test_a_card_block_holds_every_field(week):
    block = card_block(week.card("M1", 0))
    assert block[layout.TITLE][layout.VALUE_OFFSET] == "Becoming a team"
    assert block[layout.TITLE][layout.ID_OFFSET] == "aaa111"
    assert block[layout.MATERIALS][layout.VALUE_OFFSET] == "blindfolds, rope"
    assert block[layout.LOCATION][layout.FLAG_VALUE_OFFSET] == "TRUE"
    assert block[layout.NOTES][layout.FLAG_VALUE_OFFSET] == "FALSE"
    assert block[layout.DESCRIPTION][layout.FLAG_VALUE_OFFSET] == "Y"
    assert block[layout.HEROES][layout.VALUE_OFFSET] == "Dylan, Vic"


def test_an_empty_slot_renders_as_labels_only():
    block = card_block(None)
    assert block[layout.TITLE][layout.VALUE_OFFSET] == ""
    assert block[layout.TITLE][layout.LABEL_OFFSET] == "Activity"
    assert block[layout.DESCRIPTION][layout.LABEL_OFFSET] == "Description"
    assert block[layout.DESCRIPTION][layout.FLAG_VALUE_OFFSET] == Risk.NONE.value


def test_a_card_with_no_id_on_the_sheet_reads_as_having_none(week):
    grid = render_week(week)
    index = [c.name for c in week.cabins].index("M1")
    row, left = layout.card_origin(index, 0)
    grid[row][left + layout.ID_OFFSET] = ""
    parsed = parse_week(week.id, grid, render_roster(week.cabins))
    assert parsed.card("M1", 0).id == ""


def test_subtitles_survive_the_round_trip(week):
    from dataclasses import replace

    days = list(week.days)
    days[3] = replace(days[3], subtitle="Pizza Day")
    week = replace(week, days=tuple(days))
    parsed = parse_week(week.id, render_week(week), render_roster(week.cabins))
    assert parsed.days[3].subtitle == "Pizza Day"


def test_a_ragged_sheet_still_parses(week):
    grid = [row[: len(row) - 3] for row in render_week(week)]
    parsed = parse_week(week.id, grid, render_roster(week.cabins))
    assert parsed.card("M1", 0).title == "Becoming a team"


def test_roster_is_sorted_into_village_order():
    table = render_roster([Cabin("O1", "Mavis"), Cabin("M1", "Jana"), Cabin("C1", "Javi")])
    assert [c.name for c in parse_roster(table)] == ["M1", "O1", "C1"]


def test_an_empty_roster_is_an_error(week):
    with pytest.raises(LoadError):
        parse_week(week.id, render_week(week), [["Cabin", "Counselor", "Co-Counselor"]])


def test_locations_round_trip():
    locations = ("Lake - Swing", "Hot Rocks")
    assert parse_locations(render_locations(locations)) == locations


def test_card_range_matches_the_layout():
    assert card_range(0, 0) == index_to_a1(*layout.card_origin(0, 0))
    assert a1_to_index(card_range(2, 3)) == layout.card_origin(2, 3)


def test_subtitle_cell_points_at_the_subtitle_row():
    assert a1_to_index(subtitle_cell(2)) == (layout.SUBTITLE_ROW, layout.column_origin(2))


def test_a_wider_sheet_keeps_its_extra_overflow_columns(week):
    from dataclasses import replace

    wide = replace(week, overflow_columns=6)
    parsed = parse_week(wide.id, render_week(wide), render_roster(wide.cabins))
    assert parsed.overflow_columns == 6


def test_checkboxes_written_by_hand_are_understood(week):
    grid = render_week(week)
    index = [c.name for c in week.cabins].index("M1")
    row, left = layout.card_origin(index, 0)
    grid[row + layout.NOTES][left + layout.FLAG_VALUE_OFFSET] = "yes"
    parsed = parse_week(week.id, grid, render_roster(week.cabins))
    assert parsed.card("M1", 0).food


def test_materials_split_and_join(week):
    card = CabinAct(title="x", materials=("a", "b"))
    block = card_block(card)
    assert block[layout.MATERIALS][layout.VALUE_OFFSET] == "a, b"


def test_a_value_that_looks_like_a_formula_is_quoted_for_sheets():
    from brainwaves.sheets.source import literal

    assert literal("=surprise") == "'=surprise"
    assert literal("- no idea yet") == "'- no idea yet"
    assert literal("Becoming a team") == "Becoming a team"
    assert literal("TRUE") == "TRUE"
