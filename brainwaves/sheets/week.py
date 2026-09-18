"""Reading a week off the Board and Roster tabs, and writing one back.

Parsing and rendering are inverses: `parse_week(render_week(week)) == week`, which is what
`tests/test_week.py` checks. Writes go a card at a time through `card_block` so two people
editing different cards never overwrite each other.
"""

from brainwaves.model import (
    DAY_COLUMNS,
    MIN_OVERFLOW_COLUMNS,
    WEEKDAYS,
    Cabin,
    CabinAct,
    Day,
    Risk,
    Week,
    WeekId,
    sort_cabins,
)
from brainwaves.names import join_list, new_card_id, split_list
from brainwaves.sheets import layout
from brainwaves.sheets.source import LoadError, Table, cell, checkbox, index_to_a1

BOARD_TAB = "Board"
ROSTER_TAB = "Roster"
LOCATIONS_TAB = "Locations"
REQUESTS_TAB = "Support Requests"

ROSTER_HEADER = ["Cabin", "Counselor", "Co-Counselor"]


def parse_week(week_id: WeekId, board: Table, roster: Table) -> Week:
    """Build a Week from the Board and Roster tabs."""
    cabins = parse_roster(roster)
    if not cabins:
        raise LoadError(f"{ROSTER_TAB}: no cabins; add one row per cabin under {ROSTER_HEADER}")
    columns = _columns(board)
    days = tuple(
        Day(name, cell(board, layout.SUBTITLE_ROW, layout.column_origin(index)))
        for index, name in enumerate(WEEKDAYS)
    )
    cards = {}
    for cabin_index, cabin in enumerate(cabins):
        for column in range(columns):
            card = parse_card(board, cabin_index, column)
            if card is not None:
                cards[cabin.name, column] = card
    return Week(week_id, cabins, days, cards, columns - DAY_COLUMNS)


def parse_card(board: Table, cabin_index: int, column: int) -> CabinAct | None:
    """One card block, or None where the slot is empty."""
    row, left = layout.card_origin(cabin_index, column)

    def value(offset: int) -> str:
        return cell(board, row + offset, left + layout.VALUE_OFFSET)

    def flag(offset: int) -> bool:
        return checkbox(cell(board, row + offset, left + layout.FLAG_VALUE_OFFSET))

    card = CabinAct(
        id=cell(board, row, left + layout.ID_OFFSET) or new_card_id(),
        title=cell(board, row, left + layout.LABEL_OFFSET),
        description=value(layout.DESCRIPTION),
        materials=split_list(value(layout.MATERIALS)),
        location=value(layout.LOCATION),
        notes=value(layout.NOTES),
        heroes=split_list(value(layout.HEROES)),
        risk=Risk.parse(cell(board, row + layout.DESCRIPTION, left + layout.FLAG_VALUE_OFFSET)),
        van=flag(layout.TITLE),
        armory=flag(layout.MATERIALS),
        picnic=flag(layout.LOCATION),
        food=flag(layout.NOTES),
    )
    return None if card.is_blank else card


def render_week(week: Week) -> Table:
    """The whole Board tab: headings, cabin labels and every card block."""
    rows, columns = layout.grid_size(len(week.cabins), week.columns)
    grid = [["" for _ in range(columns)] for _ in range(rows)]
    grid[layout.TITLE_ROW][0] = week.id.title
    for index, day in enumerate(week.days):
        grid[layout.DAY_ROW][layout.column_origin(index)] = day.name
        grid[layout.SUBTITLE_ROW][layout.column_origin(index)] = day.subtitle
    for index in range(DAY_COLUMNS, week.columns):
        grid[layout.DAY_ROW][layout.column_origin(index)] = _overflow_name(index)
    for cabin_index, cabin in enumerate(week.cabins):
        grid[layout.cabin_row(cabin_index)][layout.CABIN_COLUMN] = cabin.label
        for column in range(week.columns):
            block = card_block(week.card(cabin.name, column))
            row, left = layout.card_origin(cabin_index, column)
            for offset, line in enumerate(block):
                grid[row + offset][left : left + layout.CARD_COLUMNS] = line
    return grid


def card_block(card: CabinAct | None) -> Table:
    """A card as the six rows by five columns the sheet holds it in."""
    if card is None:
        card = CabinAct(id="")
    values = ("", card.description, join_list(card.materials), card.location, card.notes)
    flags = (card.van, card.risk.value, card.armory, card.picnic, card.food)
    block = [
        [label, value, flag_label, _flag_text(flag), ""]
        for label, value, flag_label, flag in zip(
            layout.FIELD_LABELS[: layout.HEROES], values, layout.FLAG_LABELS, flags, strict=True
        )
    ]
    block[layout.TITLE][layout.LABEL_OFFSET] = card.title
    block[layout.TITLE][layout.ID_OFFSET] = card.id
    block.append([layout.FIELD_LABELS[layout.HEROES], join_list(card.heroes), "", "", ""])
    return block


def card_range(cabin_index: int, column: int) -> str:
    """The A1 reference of a card block's top-left cell."""
    row, left = layout.card_origin(cabin_index, column)
    return index_to_a1(row, left)


def subtitle_cell(column: int) -> str:
    """The A1 reference of a weekday's subtitle cell."""
    return index_to_a1(layout.SUBTITLE_ROW, layout.column_origin(column))


def parse_roster(table: Table) -> tuple[Cabin, ...]:
    """The Roster tab: one row per cabin, in village order whatever order it is written in."""
    cabins = []
    for row in table[1:]:
        fields = [text.strip() for text in row[:3]] + [""] * 3
        if not fields[0]:
            continue
        cabins.append(Cabin(*fields[:3]))
    return sort_cabins(cabins)


def render_roster(cabins) -> Table:
    """The Roster tab."""
    return [ROSTER_HEADER] + [[c.name, c.counselor, c.co_counselor] for c in cabins]


def parse_locations(table: Table) -> tuple[str, ...]:
    """The Locations tab: one location per row under a heading."""
    return tuple(row[0].strip() for row in table[1:] if row and row[0].strip())


def render_locations(locations) -> Table:
    """The Locations tab."""
    return [["Location"]] + [[name] for name in locations]


def _columns(board: Table) -> int:
    width = max((len(row) for row in board), default=0)
    used = max(0, width - layout.FIRST_CARD_COLUMN + layout.CARD_COLUMNS - 1) // layout.CARD_COLUMNS
    return max(used, DAY_COLUMNS + MIN_OVERFLOW_COLUMNS)


def _overflow_name(column: int) -> str:
    return f"Unplaced {column - DAY_COLUMNS + 1}"


def _flag_text(flag) -> str:
    if isinstance(flag, str):
        return flag
    return "TRUE" if flag else "FALSE"
