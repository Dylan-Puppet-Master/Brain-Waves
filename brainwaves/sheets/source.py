"""Where tables come from: one Google spreadsheet per week, or a folder of CSV files.

A table is a list of rows, each a list of cell strings, exactly as a sheet holds it.
Parsers never touch this module; they take tables.
"""

import csv
from pathlib import Path
from typing import Protocol

from brainwaves.google.retry import retrying

Table = list[list[str]]

# One batch of formatting requests. A week's board is about a hundred and sixty small ones,
# which the API takes happily in one go; the limit is for a sheet far bigger than that.
BATCH_SIZE = 250

# Just enough of a spreadsheet's metadata to name, find and size its tabs. Without a field
# mask Google sends every merge, conditional format and banding on every tab as well.
METADATA_FIELDS = "properties.title,sheets.properties(sheetId,title,gridProperties)"

# The size a tab Brain Waves adds starts at.
NEW_TAB_ROWS = 200
NEW_TAB_COLUMNS = 60


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

    def write_batch(self, writes) -> None:
        """Put blocks of cells on any tabs, given as (tab, cell, rows), in one request."""

    def ensure_tabs(self, tabs: list[str], rename_first: bool = False) -> None:
        """Make sure every tab exists; `rename_first` renames a new spreadsheet's own tab."""

    def clear(self, tab: str) -> None:
        """Empty a tab, creating it if it is missing."""

    def clear_beyond(self, tab: str, rows: int, columns: int, size: tuple[int, int]) -> None:
        """Empty whatever lies below or to the right of a block, in a tab of `size`."""

    def tab_id(self, tab: str) -> int:
        """The numeric id the Sheets API uses for a tab."""

    def size(self, tab: str, fresh: bool = True) -> tuple[int, int]:
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

    def write_batch(self, writes) -> None:
        """Overlay each block in turn."""
        for tab, cell_reference, table in writes:
            self.write(tab, table, cell_reference)

    def ensure_tabs(self, tabs: list[str], rename_first: bool = False) -> None:
        """Create an empty file for every tab that has none."""
        for tab in tabs:
            if not (self.root / f"{tab}.csv").exists():
                self._save(tab, [])

    def clear(self, tab: str) -> None:
        """Empty the file, creating it if missing."""
        self._save(tab, [])

    def clear_beyond(self, tab: str, rows: int, columns: int, size: tuple[int, int]) -> None:
        """Drop the rows and columns past the block."""
        grid = [row[:columns] for row in self.read(tab)[:rows]]
        self._save(tab, grid)

    def tab_id(self, tab: str) -> int:
        """CSV files have no tab ids; the name's position stands in for one."""
        return self.tabs().index(tab) if tab in self.tabs() else 0

    def size(self, tab: str, fresh: bool = True) -> tuple[int, int]:
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
    """One Google spreadsheet, read and written through gspread's HTTP client.

    Every API call costs a noticeable fraction of a second, so this talks to the Sheets API
    directly. gspread's `Spreadsheet` fetches the whole spreadsheet's metadata when it is
    made and again every time a tab is looked up by name; here the tab names, ids and sizes
    come from one light request and are kept, and `read_many` fetches every tab it is asked
    for in one request.
    """

    def __init__(self, http, file_id: str, title: str = "") -> None:
        self.http = http
        self.id = file_id
        self._title = title
        self._tabs: dict[str, dict] | None = None

    @property
    def title(self) -> str:
        """The spreadsheet's name."""
        if not self._title:
            self._load()
        return self._title

    def _load(self) -> dict[str, dict]:
        """Fetch the tabs' properties, and the spreadsheet's name with them."""
        metadata = retrying(
            lambda: self.http.fetch_sheet_metadata(self.id, params={"fields": METADATA_FIELDS})
        )
        self._title = metadata.get("properties", {}).get("title", "") or self._title
        self._tabs = {
            sheet["properties"]["title"]: sheet["properties"]
            for sheet in metadata.get("sheets", [])
        }
        return self._tabs

    def _worksheets(self) -> dict[str, dict]:
        return self._tabs if self._tabs is not None else self._load()

    def tabs(self) -> list[str]:
        """Worksheet titles, fetched once."""
        return list(self._worksheets())

    def tab_id(self, tab: str) -> int:
        """The worksheet's numeric id."""
        tabs = self._worksheets()
        if tab not in tabs:
            raise LoadError(f"no tab '{tab}'")
        return tabs[tab]["sheetId"]

    def size(self, tab: str, fresh: bool = True) -> tuple[int, int]:
        """The worksheet's grid size, so formatting can grow it without trimming it.

        Fresh unless the caller knows nothing else can have changed it since it was last
        fetched: someone may have added rows in Google Sheets, and those must not go.
        """
        tabs = self._load() if fresh else self._worksheets()
        if tab not in tabs:
            raise LoadError(f"no tab '{tab}'")
        grid = tabs[tab].get("gridProperties", {})
        return grid.get("rowCount", 0), grid.get("columnCount", 0)

    def read(self, tab: str) -> Table:
        """All values of one worksheet."""
        return self.read_many([tab])[tab]

    def read_many(self, tabs: list[str]) -> dict[str, Table]:
        """All values of several worksheets in one request.

        The tabs are looked up first, so a missing one is named in plain words.
        """
        if not tabs:
            return {}
        missing = [tab for tab in tabs if tab not in self._worksheets()]
        if missing:
            raise LoadError(f"no tab {', '.join(repr(t) for t in missing)}")
        return self._values(tabs)

    def read_once(self, tab: str) -> Table:
        """One tab of a spreadsheet read only this once, without listing its tabs first.

        Saves a request; a missing tab is left for Google to complain about.
        """
        return self._values([tab])[tab]

    def _values(self, tabs: list[str]) -> dict[str, Table]:
        response = retrying(
            lambda: self.http.values_batch_get(self.id, [f"'{tab}'" for tab in tabs])
        )
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
        self.write_batch([(tab, cell, table)])

    def write_batch(self, writes) -> None:
        """Put blocks of cells on any of the tabs, all in one request.

        A swap writes two cards and the Support Requests tab: five ranges and one call.
        """
        data = [
            {
                "range": f"'{tab}'!{cell_reference}",
                "values": [[literal(value) for value in row] for row in table],
            }
            for tab, cell_reference, table in writes
            if table
        ]
        if not data:
            return
        body = {"valueInputOption": "USER_ENTERED", "data": data}
        retrying(lambda: self.http.values_batch_update(self.id, body))

    def ensure_tabs(self, tabs: list[str], rename_first: bool = False) -> None:
        """Make sure every tab exists, in one request.

        A brand new spreadsheet comes with a tab of its own. `rename_first` renames it to
        the first tab wanted rather than leaving it lying about; the rest are added.
        """
        held = self._worksheets()
        requests: list[dict] = []
        renamed = None
        if rename_first and tabs and tabs[0] not in held and held:
            renamed = next(iter(held.values()))
            requests.append(
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": renamed["sheetId"], "title": tabs[0]},
                        "fields": "title",
                    }
                }
            )
        requests += [_add_tab(tab) for tab in tabs[1 if renamed else 0 :] if tab not in held]
        if not requests:
            return
        response = retrying(lambda: self.http.batch_update(self.id, {"requests": requests}))
        if renamed is not None:
            held.pop(renamed["title"])
            held[tabs[0]] = {**renamed, "title": tabs[0]}
        for reply in response.get("replies", []):
            added = (reply or {}).get("addSheet", {}).get("properties")
            if added:
                held[added["title"]] = added

    def clear_beyond(self, tab: str, rows: int, columns: int, size: tuple[int, int]) -> None:
        """Empty what lies past the block, leaving the block itself untouched.

        Clearing the whole tab and rewriting it would orphan every comment anchored to it,
        so a board that has shrunk is tidied at its edges instead. `size` is the tab's size.
        """
        held_rows, held_columns = size
        ranges = []
        if held_rows > rows:
            ranges.append(
                f"'{tab}'!{index_to_a1(rows, 0)}:{index_to_a1(held_rows - 1, held_columns - 1)}"
            )
        if held_columns > columns:
            ranges.append(
                f"'{tab}'!{index_to_a1(0, columns)}:"
                f"{index_to_a1(max(rows - 1, 0), held_columns - 1)}"
            )
        if ranges:
            retrying(lambda: self.http.values_batch_clear(self.id, body={"ranges": ranges}))

    def clear(self, tab: str) -> None:
        """Empty a worksheet, adding it if missing."""
        if tab not in self._worksheets():
            self.ensure_tabs([tab])
            return
        retrying(lambda: self.http.values_batch_clear(self.id, body={"ranges": [f"'{tab}'"]}))

    def apply(self, requests: list[dict], report=None) -> None:
        """Send raw Sheets API requests, in batches small enough not to be refused."""
        batches = [
            requests[start : start + BATCH_SIZE] for start in range(0, len(requests), BATCH_SIZE)
        ]
        for number, chunk in enumerate(batches, start=1):
            if report and len(batches) > 1:
                report(f"Formatting the board ({number} of {len(batches)})")
            retrying(lambda body={"requests": chunk}: self.http.batch_update(self.id, body))


def _add_tab(tab: str) -> dict:
    return {
        "addSheet": {
            "properties": {
                "title": tab,
                "gridProperties": {"rowCount": NEW_TAB_ROWS, "columnCount": NEW_TAB_COLUMNS},
            }
        }
    }


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


def trimmed(table: Table) -> Table:
    """A table as Sheets hands it back, with no blanks at the end of a row or the table.

    Two tables that trim the same show the same on the sheet.
    """
    rows = [list(row) for row in table]
    for row in rows:
        while row and not row[-1]:
            row.pop()
    while rows and not rows[-1]:
        rows.pop()
    return rows


def covering(table: Table, previous: Table) -> Table:
    """`table`, padded with blanks far enough to overwrite everything `previous` held.

    Writing that in place of the old contents does what clearing the tab and writing the
    new ones would, in one request instead of two.
    """
    width = max((len(row) for row in (*table, *previous)), default=0)
    height = max(len(table), len(previous))
    rows = [list(row) for row in table] + [[] for _ in range(height - len(table))]
    return [row + [""] * (width - len(row)) for row in rows]


def _ensure(grid: Table, row: int, width: int) -> None:
    while len(grid) <= row:
        grid.append([])
    line = grid[row]
    line.extend([""] * (width - len(line)))
