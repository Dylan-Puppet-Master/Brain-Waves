"""Sheets API requests that turn the Board tab into something worth looking at.

These run once, when a week is created, and again when a week grows a cabin or an overflow
column. Nothing here is needed to read a board, so a sheet that has lost its formatting
still loads.
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
VALUE_WIDTH = 230
LABEL_WIDTH = 82
FLAG_LABEL_WIDTH = 62
FLAG_VALUE_WIDTH = 46
CARD_ROW_HEIGHT = 30
TITLE_ROW_HEIGHT = 36


def board_requests(week: Week, tab_id: int, locations_tab: str) -> list[dict]:
    """Every request needed to shape the Board tab for this week's shape."""
    rows, columns = layout.grid_size(len(week.cabins), week.columns)
    return [
        *_frame(tab_id, rows, columns),
        *_widths(tab_id, week.columns),
        *_headings(tab_id, week, columns),
        *_cabin_column(tab_id, week),
        *_card_styles(tab_id, week),
        *_validation(tab_id, week, locations_tab),
        *_borders(tab_id, week),
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


def _text(size: int, color: str = INK, bold: bool = False) -> dict:
    return {"fontSize": size, "bold": bold, "foregroundColor": sheets_color(color)}


def _frame(tab_id: int, rows: int, columns: int) -> list[dict]:
    return [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": tab_id,
                    "gridProperties": {
                        "frozenRowCount": layout.FIRST_CARD_ROW,
                        "frozenColumnCount": layout.FIRST_CARD_COLUMN,
                        "rowCount": max(rows, 1),
                        "columnCount": max(columns, 1),
                    },
                }
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
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "ROWS",
                    "startIndex": layout.FIRST_CARD_ROW,
                    "endIndex": rows,
                },
                "properties": {"pixelSize": CARD_ROW_HEIGHT},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": layout.FIRST_CARD_ROW,
                },
                "properties": {"pixelSize": TITLE_ROW_HEIGHT},
                "fields": "pixelSize",
            }
        },
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
    requests = [_column_width(tab_id, layout.CABIN_COLUMN, CABIN_WIDTH)]
    for column in range(columns):
        left = layout.column_origin(column)
        requests += [
            _column_width(tab_id, left + layout.LABEL_OFFSET, LABEL_WIDTH),
            _column_width(tab_id, left + layout.VALUE_OFFSET, VALUE_WIDTH),
            _column_width(tab_id, left + layout.FLAG_LABEL_OFFSET, FLAG_LABEL_WIDTH),
            _column_width(tab_id, left + layout.FLAG_VALUE_OFFSET, FLAG_VALUE_WIDTH),
            _column_width(tab_id, left + layout.ID_OFFSET, 40, hidden=True),
        ]
    return requests


def _headings(tab_id: int, week: Week, columns: int) -> list[dict]:
    requests = [
        {
            "mergeCells": {
                "range": _range(tab_id, layout.TITLE_ROW, 0, 1, columns),
                "mergeType": "MERGE_ALL",
            }
        },
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
                {
                    "mergeCells": {
                        "range": _range(tab_id, row, left, 1, layout.VISIBLE_CARD_COLUMNS),
                        "mergeType": "MERGE_ALL",
                    }
                },
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
            {
                "mergeCells": {
                    "range": _range(tab_id, top, layout.CABIN_COLUMN, layout.CARD_ROWS, 1),
                    "mergeType": "MERGE_ALL",
                }
            },
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


def _card_styles(tab_id: int, week: Week) -> list[dict]:
    requests = []
    for index in range(len(week.cabins)):
        top = layout.cabin_row(index)
        for column in range(week.columns):
            left = layout.column_origin(column)
            requests += [
                {
                    "mergeCells": {
                        "range": _range(tab_id, top, left, 1, 2),
                        "mergeType": "MERGE_ALL",
                    }
                },
                {
                    "mergeCells": {
                        "range": _range(tab_id, top + layout.HEROES, left + 1, 1, 3),
                        "mergeType": "MERGE_ALL",
                    }
                },
                _repeat(
                    tab_id,
                    top,
                    left,
                    1,
                    2,
                    {
                        "backgroundColor": sheets_color(PANEL),
                        "wrapStrategy": "WRAP",
                        "textFormat": _text(11, INK, bold=True),
                    },
                ),
                _repeat(
                    tab_id,
                    top + 1,
                    left,
                    layout.CARD_ROWS - 1,
                    1,
                    {
                        "horizontalAlignment": "RIGHT",
                        "textFormat": _text(9, FAINT),
                    },
                ),
                _repeat(
                    tab_id,
                    top,
                    left + layout.FLAG_LABEL_OFFSET,
                    layout.CARD_ROWS - 1,
                    1,
                    {
                        "horizontalAlignment": "RIGHT",
                        "textFormat": _text(9, FAINT),
                    },
                ),
                _repeat(
                    tab_id,
                    top + layout.DESCRIPTION,
                    left + layout.FLAG_VALUE_OFFSET,
                    1,
                    1,
                    {
                        "horizontalAlignment": "CENTER",
                        "textFormat": _text(10, INK, bold=True),
                    },
                ),
                _repeat(
                    tab_id,
                    top + layout.HEROES,
                    left + 1,
                    1,
                    3,
                    {
                        "backgroundColor": sheets_color(ACCENT_SOFT),
                        "textFormat": _text(10, ACCENT),
                    },
                ),
            ]
    return requests


def _validation(tab_id: int, week: Week, locations_tab: str) -> list[dict]:
    requests = []
    for index in range(len(week.cabins)):
        top = layout.cabin_row(index)
        for column in range(week.columns):
            left = layout.column_origin(column)
            for offset in (layout.TITLE, layout.MATERIALS, layout.LOCATION, layout.NOTES):
                requests.append(
                    {
                        "setDataValidation": {
                            "range": _range(
                                tab_id, top + offset, left + layout.FLAG_VALUE_OFFSET, 1, 1
                            ),
                            "rule": {"condition": {"type": "BOOLEAN"}},
                        }
                    }
                )
            requests.append(
                {
                    "setDataValidation": {
                        "range": _range(
                            tab_id,
                            top + layout.DESCRIPTION,
                            left + layout.FLAG_VALUE_OFFSET,
                            1,
                            1,
                        ),
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [{"userEnteredValue": r.value} for r in Risk],
                            },
                            "showCustomUi": True,
                            "strict": False,
                        },
                    }
                }
            )
            requests.append(
                {
                    "setDataValidation": {
                        "range": _range(
                            tab_id, top + layout.LOCATION, left + layout.VALUE_OFFSET, 1, 1
                        ),
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_RANGE",
                                "values": [{"userEnteredValue": f"='{locations_tab}'!$A$2:$A"}],
                            },
                            "showCustomUi": True,
                            "strict": False,
                        },
                    }
                }
            )
    return requests + _risk_colors(tab_id, week)


def _risk_colors(tab_id: int, week: Week) -> list[dict]:
    rows, _ = layout.grid_size(len(week.cabins), week.columns)
    ranges = [
        _range(
            tab_id,
            layout.FIRST_CARD_ROW,
            layout.column_origin(column) + layout.FLAG_VALUE_OFFSET,
            rows - layout.FIRST_CARD_ROW,
            1,
        )
        for column in range(week.columns)
    ]
    return [
        {
            "addConditionalFormatRule": {
                "index": 0,
                "rule": {
                    "ranges": ranges,
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": value}],
                        },
                        "format": {
                            "backgroundColor": sheets_color(color),
                            "textFormat": _text(10, SURFACE, bold=True),
                        },
                    },
                },
            }
        }
        for value, color in RISK_COLORS.items()
        if value != "N"
    ]


def _borders(tab_id: int, week: Week) -> list[dict]:
    edge = {"style": "SOLID", "color": sheets_color(LINE)}
    outline = {"style": "SOLID_MEDIUM", "color": sheets_color(LINE)}
    requests = []
    for index in range(len(week.cabins)):
        top = layout.cabin_row(index)
        for column in range(week.columns):
            left = layout.column_origin(column)
            requests.append(
                {
                    "updateBorders": {
                        "range": _range(
                            tab_id, top, left, layout.CARD_ROWS, layout.VISIBLE_CARD_COLUMNS
                        ),
                        "top": outline,
                        "bottom": outline,
                        "left": outline,
                        "right": outline,
                        "innerHorizontal": edge,
                        "innerVertical": edge,
                    }
                }
            )
    return requests
