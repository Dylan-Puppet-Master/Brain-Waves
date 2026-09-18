"""Where tables come from: one Google spreadsheet per week, or a folder of CSV files.

A table is a list of rows, each a list of cell strings, exactly as a sheet holds it.
Parsers never touch this module; they take tables.
"""

import csv
from pathlib import Path
from typing import Protocol

Table = list[list[str]]

# Formatting a whole week is a large request; the API takes it more happily in pieces.
BATCH_SIZE = 25


class LoadError(Exception):
    """Bad or missing sheet data. The message names the tab and the cell or row."""


class Workbook(Protocol):
    """One week's spreadsheet: named tabs of cells, and the formatting requests to shape them."""

    def tabs(self) -> list[str]:
        """Tab names."""

    def read(self, tab: str) -> Table:
        """All cells of a tab. A missing tab raises LoadError."""

    def read_many(self, tabs: list[str]) -> dict[str, Table]:
        """Several tabs, in as few requests as possible."""

    def write(self, tab: str, table: Table, cell: str = "A1") -> None:
        """Put a block of cells at `cell`, leaving everything around it alone."""

    def clear(self, tab: str) -> None:
        """Empty a tab, creating it if it is missing."""

    def tab_id(self, tab: str) -> int:
        """The numeric id the Sheets API uses for a tab."""

    def size(self, tab: str) -> tuple[int, int]:
        """How many rows and columns the tab holds, which is not how many are filled."""

    def apply(self, requests: list[dict], report=None) -> None:
        """Send raw Sheets API requests. Where formatting is not possible, no-op."""


class CsvWorkbook:
    """Tabs stored as `<root>/<tab>.csv`, with formatting discarded. Used by the tests."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def tabs(self) -> list[str]:
        """Tab names, from the CSV file names."""
        return sorted(p.stem for p in self.root.glob("*.csv"))

    def read(self, tab: str) -> Table:
        """Rows of one CSV file."""
        path = self.root / f"{tab}.csv"
        if not path.exists():
            raise LoadError(f"no tab '{tab}' ({path} missing)")
        with path.open(newline="", encoding="utf-8") as f:
            return [list(row) for row in csv.reader(f)]

    def read_many(self, tabs: list[str]) -> dict[str, Table]:
        """Each tab's rows."""
        return {tab: self.read(tab) for tab in tabs}

    def write(self, tab: str, table: Table, cell: str = "A1") -> None:
        """Overlay a block onto the file, growing it as needed."""
        row, column = a1_to_index(cell)
        existing = self.read(tab) if (self.root / f"{tab}.csv").exists() else []
        grid = [list(line) for line in existing]
        for offset, line in enumerate(table):
            _ensure(grid, row + offset, column + len(line))
            grid[row + offset][column : column + len(line)] = line
        self._save(tab, grid)

    def clear(self, tab: str) -> None:
        """Empty the file, creating it if missing."""
        self._save(tab, [])

    def tab_id(self, tab: str) -> int:
        """CSV files have no tab ids; the name's position stands in for one."""
        return self.tabs().index(tab) if tab in self.tabs() else 0

    def size(self, tab: str) -> tuple[int, int]:
        """A CSV file is exactly as big as what is in it."""
        table = self.read(tab) if (self.root / f"{tab}.csv").exists() else []
        return len(table), max((len(row) for row in table), default=0)

    def apply(self, requests: list[dict], report=None) -> None:
        """CSV files carry no formatting."""

    def _save(self, tab: str, grid: Table) -> None:
        path = self.root / f"{tab}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(grid)


class SheetsWorkbook:
    """One Google spreadsheet, read and written through gspread.

    Every API call costs a noticeable fraction of a second, so tab names and ids are
    cached and `read_many` fetches every tab it is asked for in one request.
    """

    def __init__(self, spreadsheet) -> None:
        self.spreadsheet = spreadsheet
        self._tabs: dict[str, int] | None = None

    @property
    def id(self) -> str:
        """The Drive file id of the spreadsheet."""
        return self.spreadsheet.id

    @property
    def title(self) -> str:
        """The spreadsheet's name."""
        return self.spreadsheet.title

    def _worksheets(self) -> dict[str, int]:
        if self._tabs is None:
            self._tabs = {ws.title: ws.id for ws in self.spreadsheet.worksheets()}
        return self._tabs

    def tabs(self) -> list[str]:
        """Worksheet titles, fetched once."""
        return list(self._worksheets())

    def tab_id(self, tab: str) -> int:
        """The worksheet's numeric id."""
        ids = self._worksheets()
        if tab not in ids:
            raise LoadError(f"no tab '{tab}'")
        return ids[tab]

    def size(self, tab: str) -> tuple[int, int]:
        """The worksheet's grid size, so formatting can grow it without trimming it."""
        worksheet = self.spreadsheet.worksheet(tab)
        return worksheet.row_count, worksheet.col_count

    def read(self, tab: str) -> Table:
        """All values of one worksheet."""
        return self.read_many([tab])[tab]

    def read_many(self, tabs: list[str]) -> dict[str, Table]:
        """All values of several worksheets in one request."""
        if not tabs:
            return {}
        missing = [tab for tab in tabs if tab not in self._worksheets()]
        if missing:
            raise LoadError(f"no tab {', '.join(repr(t) for t in missing)}")
        response = self.spreadsheet.values_batch_get([f"'{tab}'" for tab in tabs])
        ranges = response.get("valueRanges", [])
        return {
            tab: [list(row) for row in value.get("values", [])]
            for tab, value in zip(tabs, ranges, strict=True)
        }

    def write(self, tab: str, table: Table, cell: str = "A1") -> None:
        """Put a block of cells at `cell`.

        Values are written as a person would type them, so TRUE becomes a checkbox; a
        value that would be read as a formula is quoted first, and Sheets gives it back
        unquoted.
        """
        if not table:
            return
        self.spreadsheet.values_update(
            f"'{tab}'!{cell}",
            params={"valueInputOption": "USER_ENTERED"},
            body={"values": [[literal(value) for value in row] for row in table]},
        )

    def clear(self, tab: str) -> None:
        """Empty a worksheet, adding it if missing."""
        import gspread

        try:
            self.spreadsheet.worksheet(tab).clear()
        except gspread.WorksheetNotFound:
            self.spreadsheet.add_worksheet(tab, rows=200, cols=60)
            self._tabs = None

    def apply(self, requests: list[dict], report=None) -> None:
        """Send raw Sheets API requests, in batches small enough not to be refused."""
        batches = [
            requests[start : start + BATCH_SIZE] for start in range(0, len(requests), BATCH_SIZE)
        ]
        for number, chunk in enumerate(batches, start=1):
            if report and len(batches) > 1:
                report(f"Formatting the board ({number} of {len(batches)})")
            self.spreadsheet.batch_update({"requests": chunk})


def a1_to_index(cell: str) -> tuple[int, int]:
    """The zero-based row and column of an A1 reference: C4 gives (3, 2)."""
    letters = "".join(c for c in cell if c.isalpha()).upper()
    digits = "".join(c for c in cell if c.isdigit())
    column = 0
    for letter in letters:
        column = column * 26 + (ord(letter) - ord("A") + 1)
    return int(digits) - 1, column - 1


def index_to_a1(row: int, column: int) -> str:
    """The A1 reference of a zero-based row and column: (3, 2) gives C4."""
    letters = ""
    column += 1
    while column:
        column, remainder = divmod(column - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return f"{letters}{row + 1}"


# A cell starting with one of these is a formula to Google Sheets, not text.
FORMULA_START = ("=", "+", "-", "@")


def literal(value: str) -> str:
    """A value Sheets will store as written, not work out."""
    return f"'{value}" if value.startswith(FORMULA_START) else value


def cell(table: Table, row: int, column: int) -> str:
    """One cell of a ragged table, blank where the sheet stops short."""
    if row >= len(table) or column >= len(table[row]):
        return ""
    return table[row][column].strip()


def checkbox(text: str) -> bool:
    """A checkbox cell. Sheets writes TRUE and FALSE; people write other things."""
    return text.strip().upper() in {"TRUE", "YES", "Y", "X", "✓"}


def _ensure(grid: Table, row: int, width: int) -> None:
    while len(grid) <= row:
        grid.append([])
    line = grid[row]
    line.extend([""] * (width - len(line)))
