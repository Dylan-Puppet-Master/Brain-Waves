"""The app's copy of one week, and every change it can make to it.

Google Sheets is the authority, but a network round trip is too slow to drag a card
against. So a change lands in `self.week` at once and its write is queued; `flush` sends
the queue, in order, from a background thread. Writes are one card block at a time, so two
villages editing different cards never overwrite each other.

Reading works the other way round. `poll` asks Drive for the file's revision, which is a
tiny answer, and reads the board only when that revision has moved. Asking every couple of
seconds therefore costs almost nothing, and someone else's edit appears about as fast as
they made it.
"""

from collections.abc import Callable
from dataclasses import replace

from brainwaves import comments as binding
from brainwaves.model import DAY_COLUMNS, CabinAct, Comment, Week
from brainwaves.names import new_card_id
from brainwaves.sheets import week as week_sheet
from brainwaves.sheets.style import board_requests
from brainwaves.sheets.support import render_support
from brainwaves.workspace import WeekSheet, Workspace


class BoardStore:
    """One week, loaded, with the comments on it."""

    def __init__(self, workspace: Workspace, sheet: WeekSheet) -> None:
        self.workspace = workspace
        self.sheet = sheet
        self.week = sheet.week
        self.locations = sheet.locations
        self.comments: list[Comment] = []
        self.staff_names: tuple[str, ...] = ()
        self.pending: list[Callable[[], None]] = []
        self.revision = ""

    @property
    def workbook(self):
        """The spreadsheet behind this week."""
        return self.sheet.workbook

    @property
    def file_id(self) -> str:
        """The Drive id of the week sheet, which comments hang off."""
        return self.workbook.id

    def load_staff(self) -> None:
        """Read the Skills doc once; a failure leaves the chips free-text."""
        try:
            self.staff_names = self.workspace.staff_names()
        except Exception:  # noqa: BLE001 - HERO chips still work without the list
            self.staff_names = ()

    @property
    def busy(self) -> bool:
        """Whether changes are still waiting to reach Google."""
        return bool(self.pending)

    def flush(self) -> None:
        """Send every queued change, oldest first. Runs off the UI thread.

        Our own writes move the revision, so the revision is taken again afterwards to
        stop the next poll reading the board back for no reason. That is only safe if
        nobody else wrote while we were editing, so the revision is checked first too;
        where somebody did, the revision is left stale and the next poll reads properly.
        """
        if not self.pending:
            return
        ours_alone = self._revision() == self.revision
        while self.pending:
            self.pending.pop(0)()
        self.revision = self._revision() if ours_alone else ""

    def poll(self) -> bool:
        """Read the board, but only if Drive says the sheet has moved since we last read it.

        The revision call is the whole point: it is small enough to make every second or
        two, where reading the board is not.
        """
        revision = self._revision()
        if revision and revision == self.revision:
            return False
        return self.reload()

    def reload(self) -> bool:
        """Read the sheet and the comments again. True if anything on the board changed."""
        revision = self._revision()
        fresh = self.workspace.read(self.workbook, self.week.id)
        changed = _contents(fresh.week) != _contents(self.week)
        self.sheet, self.week, self.locations = fresh, fresh.week, fresh.locations
        self.revision = revision
        self._adopt_new_cards()
        self.reload_comments()
        return changed

    def _revision(self) -> str:
        """Drive's revision of the week sheet, or "" if Drive would not say."""
        try:
            return self.workspace.drive.revision(self.file_id)
        except Exception:  # noqa: BLE001 - an unanswered question means read anyway
            return ""

    def _adopt_new_cards(self) -> None:
        """Give an id to every card typed straight onto the sheet, and write it back."""
        nameless = [slot for slot, card in self.week.cards.items() if not card.id]
        for cabin, column in nameless:
            card = self.week.card(cabin, column)
            self.week = self.week.place(cabin, column, replace(card, id=new_card_id()))
        if nameless:
            self._queue(lambda slots=nameless: self._write_cards(slots))

    def reload_comments(self) -> None:
        """Read the Drive threads and match them to cards."""
        try:
            threads = self.workspace.comments.list(self.file_id)
        except Exception:  # noqa: BLE001 - a board without comments still works
            return
        self.comments = binding.bind(threads, self.week, self.sheet.board_tab_id)

    def save_card(self, cabin: str, column: int, card: CabinAct | None) -> None:
        """Put a card in a slot, or clear the slot, and write that block."""
        self.week = self.week.place(cabin, column, card)
        self._queue(lambda: self._write_cards([(cabin, column)]))

    def swap(self, cabin: str, one: int, other: int) -> None:
        """Exchange two cards in the same cabin row."""
        if one == other:
            return
        self.week = self.week.swap(cabin, one, other)
        self._queue(lambda: self._write_cards([(cabin, one), (cabin, other)]))

    def set_subtitle(self, column: int, text: str) -> None:
        """Name what else is happening on a weekday."""
        if not 0 <= column < DAY_COLUMNS:
            return
        days = list(self.week.days)
        days[column] = replace(days[column], subtitle=text.strip())
        self.week = replace(self.week, days=tuple(days))
        self._queue(
            lambda: self.workbook.write(
                week_sheet.BOARD_TAB, [[text.strip()]], week_sheet.subtitle_cell(column)
            )
        )

    def set_cabins(self, cabins) -> None:
        """Replace the roster, rewriting the board so every cabin has a row."""
        self.week = replace(self.week, cabins=tuple(cabins))
        self._queue(self._write_roster)

    def add_overflow_column(self) -> None:
        """Widen the unplaced zone by one column."""
        self.week = replace(self.week, overflow_columns=self.week.overflow_columns + 1)
        self._queue(self._rewrite_board)

    def add_comment(self, card_id: str, text: str) -> None:
        """Start a thread about a card, anchored to it where Drive allows."""
        slot = self.week.locate(card_id)
        if slot is None:
            return
        cabin, column = slot
        card = self.week.card(cabin, column)
        label = next(c.label for c in self.week.cabins if c.name == cabin)
        opening = binding.opening_line(label, self._column_label(column), card.title, card_id)
        anchor = binding.anchor_for(self.week, card_id, self.sheet.board_tab_id)
        self._queue(
            lambda: self._after_comment(
                self.workspace.comments.create(self.file_id, f"{opening}\n\n{text}", anchor)
            )
        )

    def reply(self, comment_id: str, text: str) -> None:
        """Add a message to a thread."""
        self._queue(
            lambda: self._after_comment(
                self.workspace.comments.reply(self.file_id, comment_id, text)
            )
        )

    def resolve(self, comment_id: str) -> None:
        """Close a thread."""
        self._queue(
            lambda: self._after_comment(self.workspace.comments.resolve(self.file_id, comment_id))
        )

    def _after_comment(self, _result=None) -> None:
        self.reload_comments()

    def _queue(self, job) -> None:
        self.pending.append(job)

    def _write_roster(self) -> None:
        self.workbook.clear(week_sheet.ROSTER_TAB)
        self.workbook.write(week_sheet.ROSTER_TAB, week_sheet.render_roster(self.week.cabins))
        self._rewrite_board()

    def _column_label(self, column: int) -> str:
        if column < DAY_COLUMNS:
            return self.week.days[column].label
        return f"Unplaced {column - DAY_COLUMNS + 1}"

    def _write_cards(self, slots) -> None:
        index_of = {cabin.name: index for index, cabin in enumerate(self.week.cabins)}
        for cabin, column in slots:
            if cabin not in index_of:
                continue
            self.workbook.write(
                week_sheet.BOARD_TAB,
                week_sheet.card_block(self.week.card(cabin, column)),
                week_sheet.card_range(index_of[cabin], column),
            )
        self._write_support()

    def _write_support(self) -> None:
        self.workbook.clear(week_sheet.REQUESTS_TAB)
        self.workbook.write(week_sheet.REQUESTS_TAB, render_support(self.week))

    def _rewrite_board(self) -> None:
        self.workbook.clear(week_sheet.BOARD_TAB)
        self.workbook.write(week_sheet.BOARD_TAB, week_sheet.render_week(self.week))
        self.workbook.apply(
            board_requests(
                self.week,
                self.workbook.tab_id(week_sheet.BOARD_TAB),
                week_sheet.LOCATIONS_TAB,
            )
        )
        self._write_support()


def _contents(week: Week) -> tuple:
    """What a poll compares. Card ids are left out: a new one is not a change to the week."""
    cards = {slot: replace(card, id="") for slot, card in week.cards.items()}
    return (tuple(sorted(cards.items())), week.days, week.cabins, week.overflow_columns)


def week_summary(week: Week) -> str:
    """A line for the status bar: how full the week is."""
    placed = sum(1 for (_, column) in week.cards if column < DAY_COLUMNS)
    unplaced = len(week.cards) - placed
    slots = len(week.cabins) * DAY_COLUMNS
    parts = [f"{placed} of {slots} days filled"]
    if unplaced:
        parts.append(f"{unplaced} unplaced")
    return " - ".join(parts)
