"""Sheets API requests that turn the Board tab into something worth looking at.

Because every card block has the same shape, one `updateCells` request carries the format
and the data validation for a whole day column, cards and all. That keeps a week's
formatting to something like a hundred requests rather than a few thousand.

None of this is needed to read a board, so a sheet whose formatting has been lost still
loads.
"""

from brainwaves.model import DAY_COLUMNS, Risk, Week
from brainwaves.palette import (
    ACCENT,
    ACCENT_SOFT,
    FAINT,
    INK,
    LINE,
    MUTED,
    PANEL,
    RISK_COLORS,
    SURFACE,
    sheets_color,
    village_colors,
)
from brainwaves.sheets import layout

CABIN_WIDTH = 108
VALUE_WIDTH = 250
LABEL_WIDTH = 84
FLAG_LABEL_WIDTH = 62
FLAG_VALUE_WIDTH = 46
CARD_ROW_HEIGHT = 28
HEADING_ROW_HEIGHT = 34


def board_requests(
    week: Week,
    tab_id: int,
    locations_tab: str,
    new_sheet: bool = False,
    size: tuple[int, int] = (0, 0),
) -> list[dict]:
    """Every request needed to shape the Board tab for this week's shape.

    `new_sheet` also adds the conditional formats that colour the risk cells. They cover
    every row and column from the first card onward, so they never need adding again;
    adding them twice would leave the sheet with two copies of each rule.

    `size` is the tab's current row and column count, so the grid is only ever grown.
    """
    rows, columns = layout.grid_size(len(week.cabins), week.columns)
    return [
        *_frame(tab_id, rows, columns, size),
        *_widths(tab_id, week.columns),
        *_headings(tab_id, week, columns),
        *_cabin_column(tab_id, week),
        *(_card_column(tab_id, week, column, locations_tab) for column in range(week.columns)),
        *_borders(tab_id, week),
        *(_risk_colors(tab_id) if new_sheet else []),
    ]


def _range(tab_id: int, top: int, left: int, height: int, width: int) -> dict:
    return {
        "sheetId": tab_id,
        "startRowIndex": top,
        "endRowIndex": top + height,
        "startColumnIndex": left,
        "endColumnIndex": left + width,
    }


def _repeat(tab_id: int, top: int, left: int, height: int, width: int, fmt: dict) -> dict:
    return {
        "repeatCell": {
            "range": _range(tab_id, top, left, height, width),
            "cell": {"userEnteredFormat": fmt},
            "fields": "userEnteredFormat(" + ",".join(sorted(fmt)) + ")",
        }
    }


def _merge(tab_id: int, top: int, left: int, height: int, width: int) -> dict:
    return {
        "mergeCells": {"range": _range(tab_id, top, left, height, width), "mergeType": "MERGE_ALL"}
    }


def _text(size: int, color: str = INK, bold: bool = False) -> dict:
    return {"fontSize": size, "bold": bold, "foregroundColor": sheets_color(color)}


def _rows(tab_id: int, start: int, end: int, height: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": tab_id,
                "dimension": "ROWS",
                "startIndex": start,
                "endIndex": end,
            },
            "properties": {"pixelSize": height},
            "fields": "pixelSize",
        }
    }


def _frame(tab_id: int, rows: int, columns: int, size: tuple[int, int]) -> list[dict]:
    """Freeze the headings, hide the sheet's own gridlines, and make room for the board.

    The grid is only ever grown. `size` is what the tab holds now, so a tab someone has
    added rows or columns to does not have them taken away.
    """
    held_rows, held_columns = size
    return [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": tab_id,
                    "tabColorStyle": {"rgbColor": sheets_color(ACCENT)},
                    "gridProperties": {
                        "hideGridlines": True,
                        "frozenRowCount": layout.FIRST_CARD_ROW,
                        "frozenColumnCount": layout.FIRST_CARD_COLUMN,
                        "rowCount": max(rows, held_rows, 1),
                        "columnCount": max(columns, held_columns, 1),
                    },
                },
                "fields": (
                    "tabColorStyle,gridProperties(hideGridlines,frozenRowCount,"
                    "frozenColumnCount,rowCount,columnCount)"
                ),
            }
        },
        _repeat(
            tab_id,
            0,
            0,
            rows,
            columns,
            {
                "backgroundColor": sheets_color(SURFACE),
                "verticalAlignment": "MIDDLE",
                "wrapStrategy": "CLIP",
                "textFormat": _text(10),
            },
        ),
        _rows(tab_id, 0, layout.FIRST_CARD_ROW, HEADING_ROW_HEIGHT),
        _rows(tab_id, layout.FIRST_CARD_ROW, rows, CARD_ROW_HEIGHT),
    ]


def _column_width(tab_id: int, index: int, width: int, hidden: bool = False) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": tab_id,
                "dimension": "COLUMNS",
                "startIndex": index,
                "endIndex": index + 1,
            },
            "properties": {"pixelSize": width, "hiddenByUser": hidden},
            "fields": "pixelSize,hiddenByUser",
        }
    }


def _widths(tab_id: int, columns: int) -> list[dict]:
    widths = (LABEL_WIDTH, VALUE_WIDTH, FLAG_LABEL_WIDTH, FLAG_VALUE_WIDTH)
    requests = [_column_width(tab_id, layout.CABIN_COLUMN, CABIN_WIDTH)]
    for column in range(columns):
        left = layout.column_origin(column)
        requests += [_column_width(tab_id, left + n, width) for n, width in enumerate(widths)]
        requests.append(_column_width(tab_id, left + layout.ID_OFFSET, 40, hidden=True))
    return requests


def _headings(tab_id: int, week: Week, columns: int) -> list[dict]:
    requests = [
        _merge(tab_id, layout.TITLE_ROW, 0, 1, columns),
        _repeat(
            tab_id,
            layout.TITLE_ROW,
            0,
            1,
            columns,
            {
                "backgroundColor": sheets_color(ACCENT),
                "horizontalAlignment": "LEFT",
                "padding": {"left": 12},
                "textFormat": _text(13, SURFACE, bold=True),
            },
        ),
    ]
    for column in range(week.columns):
        left = layout.column_origin(column)
        weekday = column < DAY_COLUMNS
        for row, fmt in (
            (layout.DAY_ROW, _text(11, INK if weekday else MUTED, bold=True)),
            (layout.SUBTITLE_ROW, _text(10, ACCENT if weekday else FAINT)),
        ):
            requests += [
                _merge(tab_id, row, left, 1, layout.VISIBLE_CARD_COLUMNS),
                _repeat(
                    tab_id,
                    row,
                    left,
                    1,
                    layout.VISIBLE_CARD_COLUMNS,
                    {
                        "backgroundColor": sheets_color(ACCENT_SOFT if weekday else PANEL),
                        "horizontalAlignment": "CENTER",
                        "textFormat": fmt,
                    },
                ),
            ]
    return requests


def _cabin_column(tab_id: int, week: Week) -> list[dict]:
    requests = []
    for index, cabin in enumerate(week.cabins):
        line, fill = village_colors(cabin.village.label if cabin.village else "")
        top = layout.cabin_row(index)
        requests += [
            _merge(tab_id, top, layout.CABIN_COLUMN, layout.CARD_ROWS, 1),
            _repeat(
                tab_id,
                top,
                layout.CABIN_COLUMN,
                layout.CARD_ROWS,
                1,
                {
                    "backgroundColor": sheets_color(fill),
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "WRAP",
                    "textFormat": _text(11, line, bold=True),
                },
            ),
        ]
    return requests


def _card_column(tab_id: int, week: Week, column: int, locations_tab: str) -> dict:
    """Format and validation for one day's worth of cards, as a single request."""
    top = layout.FIRST_CARD_ROW
    left = layout.column_origin(column)
    rows = [
        {
            "values": [
                _cell_for(offset, position, locations_tab)
                for position in range(layout.CARD_COLUMNS)
            ]
        }
        for _ in week.cabins
        for offset in range(layout.CARD_ROWS)
    ]
    return {
        "updateCells": {
            "range": _range(
                tab_id, top, left, len(week.cabins) * layout.CARD_ROWS, layout.CARD_COLUMNS
            ),
            "rows": rows,
            "fields": "userEnteredFormat,dataValidation",
        }
    }


def _cell_for(row_offset: int, position: int, locations_tab: str) -> dict:
    """One cell of a card block: how it looks, and what it will accept."""
    cell: dict = {"userEnteredFormat": _cell_format(row_offset, position)}
    if position != layout.FLAG_VALUE_OFFSET and not (
        position == layout.VALUE_OFFSET and row_offset == layout.LOCATION
    ):
        return cell
    if position == layout.VALUE_OFFSET:
        cell["dataValidation"] = {
            "condition": {
                "type": "ONE_OF_RANGE",
                "values": [{"userEnteredValue": f"='{locations_tab}'!$A$2:$A"}],
            },
            "showCustomUi": True,
            "strict": False,
        }
        return cell
    if row_offset in layout.CHECKBOX_ROWS:
        cell["dataValidation"] = {"condition": {"type": "BOOLEAN"}}
    elif row_offset == layout.DESCRIPTION:
        cell["dataValidation"] = {
            "condition": {
                "type": "ONE_OF_LIST",
                "values": [{"userEnteredValue": risk.value} for risk in Risk],
            },
            "showCustomUi": True,
            "strict": False,
        }
    return cell


def _cell_format(row_offset: int, position: int) -> dict:
    if position == layout.ID_OFFSET:
        return {"textFormat": _text(8, FAINT)}
    if position in (layout.LABEL_OFFSET, layout.FLAG_LABEL_OFFSET):
        return {
            "backgroundColor": sheets_color(PANEL if row_offset == layout.TITLE else SURFACE),
            "horizontalAlignment": "RIGHT",
            "textFormat": _text(9, FAINT),
        }
    if position == layout.FLAG_VALUE_OFFSET:
        return {
            "backgroundColor": sheets_color(PANEL if row_offset == layout.TITLE else SURFACE),
            "horizontalAlignment": "CENTER",
            "textFormat": _text(10, INK, bold=row_offset == layout.DESCRIPTION),
        }
    looks = {
        layout.TITLE: (PANEL, _text(11, INK, bold=True)),
        layout.HEROES: (ACCENT_SOFT, _text(10, ACCENT)),
    }
    background, text = looks.get(row_offset, (SURFACE, _text(10)))
    return {
        "backgroundColor": sheets_color(background),
        "wrapStrategy": "CLIP",
        "textFormat": text,
    }


def _borders(tab_id: int, week: Week) -> list[dict]:
    """A light grid everywhere, with a firmer line around each card."""
    edge = {"style": "SOLID", "color": sheets_color(LINE)}
    outline = {"style": "SOLID_MEDIUM", "color": sheets_color(LINE)}
    height = len(week.cabins) * layout.CARD_ROWS
    width = week.columns * layout.CARD_COLUMNS
    requests = [
        {
            "updateBorders": {
                "range": _range(
                    tab_id, layout.FIRST_CARD_ROW, layout.FIRST_CARD_COLUMN, height, width
                ),
                "innerHorizontal": edge,
                "innerVertical": edge,
            }
        }
    ]
    for index in range(len(week.cabins)):
        requests.append(
            {
                "updateBorders": {
                    "range": _range(
                        tab_id,
                        layout.cabin_row(index),
                        layout.CABIN_COLUMN,
                        layout.CARD_ROWS,
                        width + 1,
                    ),
                    "top": outline,
                    "bottom": outline,
                }
            }
        )
    for column in range(week.columns):
        requests.append(
            {
                "updateBorders": {
                    "range": _range(
                        tab_id,
                        layout.FIRST_CARD_ROW,
                        layout.column_origin(column),
                        height,
                        layout.VISIBLE_CARD_COLUMNS,
                    ),
                    "left": outline,
                    "right": outline,
                }
            }
        )
    return requests


def _risk_colors(tab_id: int) -> list[dict]:
    """Colour a risk cell by what it says, so a red week is visible from across the room.

    The ranges are open ended: every row and column from the first card onward. A risk
    letter is the whole of its cell and appears nowhere else on the board, and growing the
    board does not need the rules rewritten.
    """
    ranges = [
        {
            "sheetId": tab_id,
            "startRowIndex": layout.FIRST_CARD_ROW,
            "startColumnIndex": layout.FIRST_CARD_COLUMN,
        }
    ]
    return [
        {
            "addConditionalFormatRule": {
                "index": 0,
                "rule": {
                    "ranges": ranges,
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": value}]},
                        "format": {
                            "backgroundColor": sheets_color(color),
                            "textFormat": _text(10, SURFACE, bold=True),
                        },
                    },
                },
            }
        }
        for value, color in RISK_COLORS.items()
        if value != Risk.NONE.value
    ]
