"""The app's copy of one week, and every change it can make to it.

Google Sheets is the authority, but a network round trip is too slow to drag a card
against. So a change lands in `self.week` at once and its write is queued; `flush` sends
the queue, in order, from a background thread. Writes are one card block at a time, so two
villages editing different cards never overwrite each other.

Card writes are gathered rather than queued one by one. A card write sends whatever the
card holds when it runs, not when it was asked for, so five cards dragged while a poll was
in flight need one request between them, not five. The Support Requests tab rides along in
that same request, and only when what it says has actually changed: most edits - a
description, some materials, a note - change nothing on it.

Reading is done by simply reading. `poll` fetches the Board, Roster and Locations tabs in
one request and compares them to what is held; a full board is about sixty kilobytes,
which is affordable every few seconds and is the only thing that is reliable.

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
from threading import RLock

from brainwaves import comments as binding
from brainwaves.model import DAY_COLUMNS, EXTRA, CabinAct, Comment, Week
from brainwaves.names import new_card_id
from brainwaves.sheets import layout
from brainwaves.sheets import week as week_sheet
from brainwaves.sheets.source import covering, trimmed
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
        self.pending: list[Callable[[], None]] = []
        self._lock = RLock()
        # Slots and weekday subtitles changed here and not yet written.
        self._dirty: set[tuple[str, int]] = set()
        self._dirty_days: set[int] = set()
        # The Support Requests tab as the sheet holds it, trimmed, or None if not known; and
        # the layout its formatting was last put in for, or None if not known.
        self._support = sheet.support
        self._support_shape: tuple | None = None
        # Set once Drive says the sheet has been deleted or put in the trash.
        self.gone = False

    @property
    def workbook(self):
        """The spreadsheet behind this week."""
        return self.sheet.workbook

    @property
    def file_id(self) -> str:
        """The Drive id of the week sheet, which comments hang off."""
        return self.workbook.id

    @property
    def staff(self) -> StaffLists:
        """The staff lists, read once for every week; empty until they have been."""
        return self.workspace.staff or StaffLists()

    @property
    def busy(self) -> bool:
        """Whether changes are still waiting to reach Google."""
        return bool(self.pending)

    def flush(self) -> None:
        """Send every queued change, oldest first. Runs off the UI thread."""
        while True:
            with self._lock:
                if self.gone:
                    self.pending.clear()
                if not self.pending:
                    return
                job = self.pending.pop(0)
            job()

    def poll(self) -> bool:
        """Read the week. True if anything on the board changed.

        A card dragged while this was reading leaves a write waiting, and then what was
        read is already out of date, so it is dropped and the next poll reads again.
        """
        return self._read(keep_pending=True)

    def reload(self) -> bool:
        """Read every tab and the comments again. True if anything on the board changed."""
        changed = self._read(keep_pending=False)
        self.reload_comments()
        return changed

    def _read(self, keep_pending: bool) -> bool:
        """Read the week and hold it. True if the board is not what it was.

        `keep_pending` throws the read away if changes are waiting to be written.
        """
        fresh = self.workspace.read(self.workbook, self.week.id)
        with self._lock:
            if keep_pending and self.pending:
                return False
            changed = _contents(fresh.week) != _contents(self.week)
            self.sheet, self.week, self.locations = fresh, fresh.week, fresh.locations
            if fresh.support != self._support:
                # Somebody else wrote it, and formatted it for their layout, not ours.
                self._support, self._support_shape = fresh.support, None
        self._adopt_new_cards()
        return changed

    def _adopt_new_cards(self) -> None:
        """Give an id to every card typed straight onto the sheet, and write it back."""
        with self._lock:
            nameless = [slot for slot, card in self.week.cards.items() if not card.id]
            for cabin, column in nameless:
                card = self.week.card(cabin, column)
                self.week = self.week.place(cabin, column, replace(card, id=new_card_id()))
            if nameless:
                self._queue_cards(nameless)

    def reload_comments(self) -> None:
        """Check the sheet is still there, then read the Drive threads and match them to cards.

        Sheets carries on reading and writing a spreadsheet in the trash, so without asking
        Drive a deleted week would go on syncing with nobody. This rides on the comments'
        slower beat, which talks to Drive anyway.
        """
        try:
            if not self.workspace.still_there(self.file_id):
                self.gone = True
                return
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
            self._queue_cards([(cabin, column)])
        if gone is not None and (card is None or card.id != gone.id):
            self.close_threads(gone.id, gone.title)

    def close_threads(self, card_id: str, title: str) -> None:
        """Answer and resolve every open thread about a card that has gone."""
        threads = [c for c in self.comments if c.card_id == card_id and not c.resolved]
        if threads:
            self._queue(lambda: self._finish(threads, title))
            self._queue_last(self.reload_comments)

    def _finish(self, threads, title: str) -> None:
        subject = title or "the activity"
        for thread in threads:
            self.workspace.comments.resolve(
                self.file_id, thread.id, f"{subject} was deleted, so this is closed."
            )

    def swap(self, cabin: str, one: int, other: int) -> None:
        """Exchange two cards in the same cabin row."""
        if one == other:
            return
        with self._lock:
            self.week = self.week.swap(cabin, one, other)
            self._queue_cards([(cabin, one), (cabin, other)])

    def set_subtitle(self, column: int, text: str) -> None:
        """Name what else is happening on a weekday."""
        if not 0 <= column < DAY_COLUMNS:
            return
        with self._lock:
            days = list(self.week.days)
            days[column] = replace(days[column], subtitle=text.strip())
            self.week = replace(self.week, days=tuple(days))
            self._dirty_days.add(column)
            self._queue_once(self._write_dirty)

    def set_cabins(self, cabins) -> None:
        """Replace the roster, rewriting the board so every cabin has a row."""
        with self._lock:
            self.week = replace(self.week, cabins=tuple(cabins))
            self._queue_once(self._write_roster)

    def add_overflow_column(self) -> None:
        """Widen the unplaced zone by one column."""
        with self._lock:
            self.week = replace(self.week, overflow_columns=self.week.overflow_columns + 1)
            self._queue_once(self._rewrite_board)

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
            lambda: self.workspace.comments.create(self.file_id, f"{opening}\n\n{text}", anchor)
        )
        self._queue_last(self.reload_comments)

    def reply(self, comment_id: str, text: str) -> None:
        """Add a message to a thread."""
        self._queue(lambda: self.workspace.comments.reply(self.file_id, comment_id, text))
        self._queue_last(self.reload_comments)

    def resolve(self, comment_id: str) -> None:
        """Close a thread."""
        self._queue(lambda: self.workspace.comments.resolve(self.file_id, comment_id))
        self._queue_last(self.reload_comments)

    def _queue(self, job) -> None:
        with self._lock:
            self.pending.append(job)

    def _queue_once(self, job) -> None:
        """Queue a job that sends the state as it is when it runs, unless one is waiting.

        The one already waiting will send this change too, and sooner.
        """
        with self._lock:
            if job not in self.pending:
                self.pending.append(job)

    def _queue_last(self, job) -> None:
        """Queue a job to run after everything queued so far, and only once."""
        with self._lock:
            if job in self.pending:
                self.pending.remove(job)
            self.pending.append(job)

    def _queue_cards(self, slots) -> None:
        with self._lock:
            self._dirty.update(slots)
            self._queue_once(self._write_dirty)

    def _write_roster(self) -> None:
        self.workbook.clear(week_sheet.ROSTER_TAB)
        with self._lock:
            roster = week_sheet.render_roster(self.week.cabins)
        self._rewrite_board([(week_sheet.ROSTER_TAB, "A1", roster)])

    def _column_label(self, column: int) -> str:
        return self.week.days[column].label if column < DAY_COLUMNS else EXTRA

    def _write_dirty(self) -> None:
        """Write every card and subtitle changed since the last write, in one request.

        Data cells only: see `week_sheet.card_ranges` for why the labels are left alone.
        """
        with self._lock:
            slots, self._dirty = self._dirty, set()
            days, self._dirty_days = self._dirty_days, set()
            week = self.week
        index_of = {cabin.name: index for index, cabin in enumerate(week.cabins)}
        writes = [
            (week_sheet.BOARD_TAB, cell_reference, rows)
            for cabin, column in sorted(slots)
            if cabin in index_of
            for cell_reference, rows in week_sheet.card_ranges(
                index_of[cabin], column, week.card(cabin, column)
            )
        ]
        writes += [
            (week_sheet.BOARD_TAB, week_sheet.subtitle_cell(column), [[week.days[column].subtitle]])
            for column in sorted(days)
        ]
        self._send(week, writes)

    def _rewrite_board(self, extra=()) -> None:
        """Lay the whole board out again, for a change of shape rather than of content."""
        with self._lock:
            week = self.week
        rows, columns = layout.grid_size(len(week.cabins), week.columns)
        size = self.workbook.size(week_sheet.BOARD_TAB)
        # Only what lies past the new board is cleared, so this may go before or after it.
        self.workbook.clear_beyond(week_sheet.BOARD_TAB, rows, columns, size=size)
        self._send(
            week,
            [*extra, (week_sheet.BOARD_TAB, "A1", week_sheet.render_week(week))],
            formats=board_requests(
                week,
                self.workbook.tab_id(week_sheet.BOARD_TAB),
                week_sheet.LOCATIONS_TAB,
                size=size,
            ),
        )

    def _send(self, week: Week, writes, formats=()) -> None:
        """Write these cells and the Support Requests tab in one request, then format.

        The tab is written only if it would say something new, and formatted only if its
        day blocks have moved. If anything goes wrong, what the sheet holds is no longer
        known, so the next write puts the whole tab back.
        """
        view = render_support(week)
        wanted = trimmed(view.table)
        formats = list(formats)
        try:
            if wanted != self._support:
                if self._support is None:
                    self.workbook.clear(week_sheet.REQUESTS_TAB)
                previous = self._support or []
                writes = [*writes, (week_sheet.REQUESTS_TAB, "A1", covering(view.table, previous))]
                shape = (tuple(view.day_rows), tuple(view.header_rows), tuple(view.quiet_rows))
                if shape != self._support_shape:
                    formats += support_requests(view, self.workbook.tab_id(week_sheet.REQUESTS_TAB))
                self._support, self._support_shape = wanted, shape
            self.workbook.write_batch(writes)
            if formats:
                self.workbook.apply(formats)
        except Exception:
            self._support = self._support_shape = None
            raise


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
