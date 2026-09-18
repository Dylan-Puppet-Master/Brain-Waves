"""An offline stand-in for Google: CSV tabs on disk and comments in a list."""

import hashlib
from datetime import datetime
from pathlib import Path

from brainwaves.google.comments import RawComment, RawReply
from brainwaves.sheets import week as week_sheet
from brainwaves.sheets.source import CsvWorkbook
from brainwaves.workspace import WeekSheet, write_template


class FakeComments:
    def __init__(self):
        self.threads: list[RawComment] = []

    def list(self, file_id):
        return list(self.threads)

    def create(self, file_id, text, anchor=""):
        made = RawComment(f"c{len(self.threads)}", "Kestrel", _now(), text, False, anchor, ())
        self.threads.append(made)
        return made

    def reply(self, file_id, comment_id, text):
        for index, thread in enumerate(self.threads):
            if thread.id == comment_id:
                reply = RawReply(f"r{len(thread.replies)}", "Dylan", _now(), text)
                self.threads[index] = _replace(thread, replies=thread.replies + (reply,))

    def resolve(self, file_id, comment_id):
        for index, thread in enumerate(self.threads):
            if thread.id == comment_id:
                self.threads[index] = _replace(thread, resolved=True)


TAB_IDS = {
    week_sheet.BOARD_TAB: 0,
    week_sheet.ROSTER_TAB: 1,
    week_sheet.LOCATIONS_TAB: 2,
    week_sheet.REQUESTS_TAB: 3,
}


class FakeWorkbook(CsvWorkbook):
    """A CSV workbook that also answers the few spreadsheet-shaped questions the store asks.

    It keeps the formatting requests it is given. They do nothing to a CSV file, but a test
    can check that they were built and aimed at the right tab.
    """

    id = "fake-file"
    title = "Cabin Act Sorting - S2W1"

    def __init__(self, root):
        super().__init__(root)
        self.applied: list[dict] = []

    class _Spreadsheet:
        def __init__(self, workbook):
            self.workbook = workbook

        @property
        def sheet1(self):
            return self

        def update_title(self, title):
            self.workbook.clear(title)

    @property
    def spreadsheet(self):
        return self._Spreadsheet(self)

    def tab_id(self, tab):
        return TAB_IDS.get(tab, 9)

    def apply(self, requests, report=None):
        self.applied.extend(requests)


class FakeDrive:
    """Stands in for Drive.

    `frozen` is the point of it: Google Sheets does not update a file's Drive metadata
    promptly when a cell is edited in the browser, so nothing in Brain Waves may depend on
    that metadata to decide whether to read.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.frozen = False
        self.asked = 0

    def revision(self, file_id):
        self.asked += 1
        if self.frozen:
            return "unchanged"
        blob = b"".join(sorted(path.read_bytes() for path in self.root.glob("*.csv")))
        return hashlib.sha1(blob).hexdigest()


class FakeWorkspace:
    """Reads and writes a folder of CSV files instead of a Google spreadsheet."""

    def __init__(self, root, names=("Dylan", "Vic", "Catana")):
        self.root = root
        self.comments = FakeComments()
        self.drive = FakeDrive(root)
        self.names = names

    def read(self, workbook, week_id):
        tabs = [week_sheet.BOARD_TAB, week_sheet.ROSTER_TAB, week_sheet.LOCATIONS_TAB]
        tables = workbook.read_many(tabs)
        cabins = week_sheet.parse_roster(tables[week_sheet.ROSTER_TAB])
        week = week_sheet.parse_week(week_id, tables[week_sheet.BOARD_TAB], cabins)
        return WeekSheet(
            workbook, week, week_sheet.parse_locations(tables[week_sheet.LOCATIONS_TAB])
        )

    def read_board(self, sheet, cabins=None):
        board = sheet.workbook.read(week_sheet.BOARD_TAB)
        week = week_sheet.parse_week(sheet.week.id, board, cabins or sheet.week.cabins)
        return WeekSheet(sheet.workbook, week, sheet.locations)

    def staff_names(self):
        return self.names


def build(root, week, locations=("Hot Rocks", "Low Ropes 1")) -> tuple[FakeWorkspace, WeekSheet]:
    """A workspace holding one week, written out as the template would write it."""
    workbook = FakeWorkbook(root)
    write_template(workbook, week, locations)
    workspace = FakeWorkspace(root)
    return workspace, workspace.read(workbook, week.id)


def _now():
    return datetime.now().astimezone()


def _replace(thread, **changes):
    from dataclasses import replace

    return replace(thread, **changes)
