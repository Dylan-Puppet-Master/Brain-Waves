"""The app's copy of one week, and every change it can make to it.

Google Sheets is the authority, but a network round trip is too slow to drag a card
against. So a change lands in `self.week` at once and its write is queued; `flush` sends
the queue, in order, from a background thread. Writes are one card block at a time, so two
villages editing different cards never overwrite each other.

Reading is done by simply reading. `poll` fetches the Board tab and compares it to what is
held; a full board is about sixty kilobytes, which is affordable every few seconds and is
the only thing that is reliable.

Google Sheets does not update its Drive file metadata promptly when someone edits a cell in
the browser, so `modifiedTime` and `version` cannot be used to decide whether to read. An
earlier version of this file did exactly that, and edits made in Google Sheets went
unnoticed for minutes or were missed altogether.

The week is read on a background thread and changed on the window's thread, so the two are
kept apart by `_lock`. It is held only long enough to swap one immutable `Week` for
another, never across a network call, and a read that finishes to find unwritten changes
waiting is thrown away rather than allowed to undo them.
"""

from collections.abc import Callable
from dataclasses import replace
from threading import Lock

from brainwaves import comments as binding
from brainwaves.model import DAY_COLUMNS, EXTRA, CabinAct, Comment, Week
from brainwaves.names import new_card_id
from brainwaves.sheets import layout
from brainwaves.sheets import week as week_sheet
from brainwaves.sheets.staff import StaffLists
from brainwaves.sheets.style import board_requests, support_requests
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
        self.staff = StaffLists()
        self.pending: list[Callable[[], None]] = []
        self._lock = Lock()

    @property
    def workbook(self):
        """The spreadsheet behind this week."""
        return self.sheet.workbook

    @property
    def file_id(self) -> str:
        """The Drive id of the week sheet, which comments hang off."""
        return self.workbook.id

    def load_staff(self) -> None:
        """Read the staff documents once; a failure leaves the chips free text."""
        try:
            self.staff = self.workspace.staff_lists()
        except Exception:  # noqa: BLE001 - HERO chips still work without the lists
            self.staff = StaffLists()

    @property
    def busy(self) -> bool:
        """Whether changes are still waiting to reach Google."""
        return bool(self.pending)

    def flush(self) -> None:
        """Send every queued change, oldest first. Runs off the UI thread."""
        while True:
            with self._lock:
                if not self.pending:
                    return
                job = self.pending.pop(0)
            job()

    def poll(self) -> bool:
        """Read the board. True if anything on it changed.

        Only the Board tab: it is the one people move cards on, and the one that has to be
        current within a few seconds. A card dragged while this was reading leaves a write
        waiting, and then what was read is already out of date, so it is dropped and the
        next poll reads again.

        The cabins come from the week in hand rather than from the sheet last read, which
        may not know about a cabin added since.
        """
        fresh = self.workspace.read_board(self.sheet, self.week.cabins)
        with self._lock:
            if self.pending:
                return False
            changed = _contents(fresh.week) != _contents(self.week)
            self.sheet, self.week = fresh, fresh.week
        self._adopt_new_cards()
        return changed

    def reload(self) -> bool:
        """Read every tab and the comments again. True if anything on the board changed."""
        fresh = self.workspace.read(self.workbook, self.week.id)
        with self._lock:
            changed = _contents(fresh.week) != _contents(self.week)
            self.sheet, self.week, self.locations = fresh, fresh.week, fresh.locations
        self._adopt_new_cards()
        self.reload_comments()
        return changed

    def reload_reference(self) -> bool:
        """Read the cabins, the locations and the comments. True if the cabins changed.

        These change once a session, where the board changes all afternoon, so they are
        read on their own slower beat.
        """
        fresh = self.workspace.read(self.workbook, self.week.id)
        with self._lock:
            changed = fresh.week.cabins != self.week.cabins
            self.locations = fresh.locations
            if changed and not self.pending:
                self.sheet, self.week = fresh, fresh.week
            else:
                changed = False
        if changed:
            self._adopt_new_cards()
        self.reload_comments()
        return changed

    def _adopt_new_cards(self) -> None:
        """Give an id to every card typed straight onto the sheet, and write it back."""
        with self._lock:
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
        """Put a card in a slot, or clear the slot, and write that block.

        A card that goes takes its discussion with it: the threads about it are answered
        saying so and closed, rather than left open about an activity nobody can see.
        """
        with self._lock:
            gone = self.week.card(cabin, column)
            self.week = self.week.place(cabin, column, card)
            self._queue(lambda: self._write_cards([(cabin, column)]))
        if gone is not None and (card is None or card.id != gone.id):
            self.close_threads(gone.id, gone.title)

    def close_threads(self, card_id: str, title: str) -> None:
        """Answer and resolve every open thread about a card that has gone."""
        threads = [c for c in self.comments if c.card_id == card_id and not c.resolved]
        if threads:
            self._queue(lambda: self._finish(threads, title))

    def _finish(self, threads, title: str) -> None:
        subject = title or "the activity"
        for thread in threads:
            self.workspace.comments.reply(
                self.file_id, thread.id, f"{subject} was deleted, so this is closed."
            )
            self.workspace.comments.resolve(self.file_id, thread.id)
        self.reload_comments()

    def swap(self, cabin: str, one: int, other: int) -> None:
        """Exchange two cards in the same cabin row."""
        if one == other:
            return
        with self._lock:
            self.week = self.week.swap(cabin, one, other)
            self._queue(lambda: self._write_cards([(cabin, one), (cabin, other)]))

    def set_subtitle(self, column: int, text: str) -> None:
        """Name what else is happening on a weekday."""
        if not 0 <= column < DAY_COLUMNS:
            return
        with self._lock:
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
        with self._lock:
            self.week = replace(self.week, cabins=tuple(cabins))
            self._queue(self._write_roster)

    def add_overflow_column(self) -> None:
        """Widen the unplaced zone by one column."""
        with self._lock:
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
        return self.week.days[column].label if column < DAY_COLUMNS else EXTRA

    def _write_cards(self, slots) -> None:
        """Write the cards in these slots, in one request, data cells only."""
        index_of = {cabin.name: index for index, cabin in enumerate(self.week.cabins)}
        blocks = []
        for cabin, column in slots:
            if cabin in index_of:
                card = self.week.card(cabin, column)
                blocks += week_sheet.card_ranges(index_of[cabin], column, card)
        self.workbook.write_many(week_sheet.BOARD_TAB, blocks)
        self._write_support()

    def _write_support(self) -> None:
        view = render_support(self.week)
        self.workbook.clear(week_sheet.REQUESTS_TAB)
        self.workbook.write(week_sheet.REQUESTS_TAB, view.table)
        self.workbook.apply(support_requests(view, self.workbook.tab_id(week_sheet.REQUESTS_TAB)))

    def _rewrite_board(self) -> None:
        """Lay the whole board out again, for a change of shape rather than of content."""
        rows, columns = layout.grid_size(len(self.week.cabins), self.week.columns)
        self.workbook.write(week_sheet.BOARD_TAB, week_sheet.render_week(self.week))
        self.workbook.clear_beyond(week_sheet.BOARD_TAB, rows, columns)
        self.workbook.apply(
            board_requests(
                self.week,
                self.workbook.tab_id(week_sheet.BOARD_TAB),
                week_sheet.LOCATIONS_TAB,
                size=self.workbook.size(week_sheet.BOARD_TAB),
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
