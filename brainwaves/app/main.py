"""The Brain Waves window.

It holds one week at a time. Google is reached only through `JobQueue`, so the board stays
responsive; every job's result comes back to `_job_done` and is turned into what the window
shows.
"""

import sys

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from brainwaves import __version__
from brainwaves import comments as binding
from brainwaves.app.activity import sweeping_bar
from brainwaves.app.board import BoardView
from brainwaves.app.comment_panel import CommentPanel
from brainwaves.app.conflict_panel import ConflictPanel
from brainwaves.app.dialogs import FolderDialog, RosterDialog
from brainwaves.app.editor import CardForm, CardZoom
from brainwaves.app.stats import StatsPanel
from brainwaves.app.sync import JobQueue
from brainwaves.app.theme import apply_theme
from brainwaves.app.welcome import WelcomePage
from brainwaves.config import Config, State, load_config, load_state, save_state, with_week
from brainwaves.conflicts import find_conflicts
from brainwaves.google import auth
from brainwaves.model import DAY_COLUMNS, EXTRA, CabinAct, WeekId
from brainwaves.store import BoardStore, week_summary
from brainwaves.update import download, install, latest_release
from brainwaves.workspace import Workspace

SIGN_IN = "Sign in with Google"
CONFIG_HELP = "Brain Waves needs a Google OAuth client in config.toml. See the install guide."

# Jobs that happen on a timer. They light no indicator and raise no dialog, because at a
# couple of seconds apart an indicator that blinks constantly stops meaning anything.
QUIET_JOBS = {"sync", "comments", "staff", "update-quiet"}

# How long the session and week boxes wait for the clicking to stop before opening a week,
# so stepping from week 1 to week 4 opens week 4 rather than weeks 2, 3 and 4 in turn.
PICK_DELAY_MS = 350

# While the window is in the background, the board is read this many times less often.
# Coming back to the window reads it at once, so nobody sees the difference; Google's
# quota does.
BACKGROUND_SLOWDOWN = 4


def run_app(config: Config | None = None) -> int:
    """Open the window and run until it closes."""
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow(config or load_config())
    window.show()
    window.start()
    return app.exec()


class MainWindow(QMainWindow):
    """The board, the comments panel, and the toolbar that picks the week."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.state: State = load_state()
        self.workspace: Workspace | None = None
        self.store: BoardStore | None = None
        self.selected_card: str | None = None
        self.comments_pending = False
        # Every week opened this run, so going back to one draws at once and reads after.
        self.stores: dict[WeekId, BoardStore] = {}
        self.checked_for_updates = False
        self.setWindowTitle("Brain Waves")
        self.resize(1440, 900)

        self.jobs = JobQueue()
        self.jobs.done.connect(self._job_done)
        self.jobs.failed.connect(self._job_failed)
        self.jobs.progress.connect(self._job_progress)
        self.jobs.idle.connect(self._settle)
        self.jobs.start()
        self.running: set[str] = set()

        self.board = BoardView()
        self.board.card_picked.connect(self.select_card)
        self.board.card_edit.connect(self.edit_card)
        self.board.swap_requested.connect(self.swap_cards)
        self.board.add_requested.connect(self.add_card)
        self.board.subtitle_changed.connect(self.set_subtitle)
        self.board.overflow_requested.connect(self.add_overflow)
        self.board.stats_requested.connect(self.show_stats)
        self.zoom = CardZoom(self.board)
        self.zoom.saved.connect(self._save_edit)
        self.editing: tuple[str, int] | None = None
        # The statistics zoom out of the corner of the board the way a card does from its slot.
        self.stats_zoom = CardZoom(self.board)
        self.welcome = WelcomePage()
        self.welcome.acted.connect(self._welcome_action)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.welcome)
        self.pages.addWidget(self.board)
        self.activity = sweeping_bar()
        self.activity.hide()
        centre = QWidget()
        stack = QVBoxLayout(centre)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)
        stack.addWidget(self.activity)
        stack.addWidget(self.pages, 1)
        self.setCentralWidget(centre)

        self.comments = CommentPanel()
        self.comments.comment_added.connect(self.add_comment)
        self.comments.reply_added.connect(self.reply_to_comment)
        self.comments.resolved.connect(self.resolve_comment)
        dock = QDockWidget("Comments", self)
        dock.setObjectName("commentsDock")
        dock.setWidget(self.comments)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.conflicts = ConflictPanel()
        self.conflicts.picked.connect(self.board.show_clash)
        clashes = QDockWidget("Clashes", self)
        clashes.setObjectName("clashesDock")
        clashes.setWidget(self.conflicts)
        clashes.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.splitDockWidget(dock, clashes, Qt.Vertical)
        self.resizeDocks([dock, clashes], [3, 2], Qt.Vertical)

        self._build_toolbar()
        self.poll = QTimer(self)
        self.poll_interval = max(self.config.poll_seconds, 1) * 1000
        self.poll.setInterval(self.poll_interval)
        self.poll.timeout.connect(self._poll)
        self.comment_poll = QTimer(self)
        self.comment_poll.setInterval(max(self.config.comment_poll_seconds, 1) * 1000)
        self.comment_poll.timeout.connect(self._poll_comments)
        self.pick = QTimer(self)
        self.pick.setSingleShot(True)
        self.pick.setInterval(PICK_DELAY_MS)
        self.pick.timeout.connect(self.open_week)
        self._welcome_step = SIGN_IN

    def start(self) -> None:
        """Pick up where the last run left off: sign in, then open the week."""
        credentials = auth.saved_credentials()
        if credentials is None:
            self._show_welcome(
                "Sign in with the Google account that can open the cabin act sheets.",
                SIGN_IN,
                "" if self.config.has_client else CONFIG_HELP,
            )
            return
        self._signed_in(credentials)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Let queued writes finish before the window goes."""
        self._stop_polling()
        for store in self.stores.values():
            if store.busy:
                self.jobs.submit("flush", store.flush)
        self.jobs.stop()
        super().closeEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Read the board less often in the background, and at once on coming back."""
        super().changeEvent(event)
        if event.type() != QEvent.ActivationChange:
            return
        if not self.isActiveWindow():
            self.poll.setInterval(self.poll_interval * BACKGROUND_SLOWDOWN)
        elif self.poll.interval() != self.poll_interval:
            self.poll.setInterval(self.poll_interval)
            if self.poll.isActive():
                self._poll()

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main")
        bar.setObjectName("chrome")
        bar.setMovable(False)
        self.addToolBar(bar)
        wordmark = QLabel("Brain Waves")
        wordmark.setObjectName("wordmark")
        bar.addWidget(wordmark)
        bar.addWidget(QLabel("Session"))
        self.session_box = _counter(self.state.session)
        self.week_box = _counter(self.state.week)
        self.session_box.valueChanged.connect(lambda _value: self.pick.start())
        self.week_box.valueChanged.connect(lambda _value: self.pick.start())
        bar.addWidget(self.session_box)
        bar.addWidget(QLabel("Week"))
        bar.addWidget(self.week_box)
        self.sheet_label = QLabel("")
        self.sheet_label.setObjectName("sheetName")
        bar.addWidget(self.sheet_label)
        bar.addSeparator()
        self.link_button = _button("Link to Google Sheets", self.link_folder)
        self.roster_button = _button("Cabins", self.edit_roster)
        self.refresh_button = _button("Refresh", self.refresh)
        for button in (self.link_button, self.roster_button, self.refresh_button):
            bar.addWidget(button)
        bar.addWidget(_stretch())
        self.status = QLabel("")
        self.status.setObjectName("status")
        bar.addWidget(self.status)
        bar.addWidget(_button("Check for updates", self.check_for_updates))

    def _show_welcome(self, message: str, action: str, detail: str = "") -> None:
        self._welcome_step = action
        self.welcome.show_step(message, action, detail)
        self.pages.setCurrentWidget(self.welcome)
        self._set_busy("")

    def _welcome_action(self) -> None:
        if self._welcome_step == SIGN_IN:
            self.sign_in()
        elif self._welcome_step == "Link to Google Sheets":
            self.link_folder()
        else:
            self.start_new_week()

    def sign_in(self) -> None:
        """Ask Google for permission, in the browser, off the UI thread."""
        self.welcome.show_working(
            "Finishing sign-in in your browser",
            "Brain Waves is waiting for Google. It carries on once you are done.",
        )
        self.pages.setCurrentWidget(self.welcome)
        self._submit("signin", lambda: auth.sign_in(self.config), "Waiting for Google...")

    def _signed_in(self, credentials) -> None:
        self.workspace = Workspace(credentials, self.config)
        if not self.state.folder_id:
            self._show_welcome(
                "Choose the Google Drive folder that holds the Cabin Act Sorting sheets.",
                "Link to Google Sheets",
            )
            return
        self.open_week()

    def link_folder(self) -> None:
        """Browse Drive and remember the folder the week sheets live in."""
        if self.workspace is None:
            return
        dialog = FolderDialog(self.workspace.drive, self)
        if dialog.exec() != FolderDialog.Accepted:
            return
        folder_id, name = dialog.folder
        self.state = State(folder_id, name, self.state.session, self.state.week)
        self.stores.clear()
        save_state(self.state)
        self.open_week()

    def open_week(self) -> None:
        """Load the session and week the toolbar shows."""
        if self.workspace is None or not self.state.folder_id:
            return
        self.state = with_week(self.state, self.session_box.value(), self.week_box.value())
        save_state(self.state)
        week_id = WeekId(self.state.session, self.state.week)
        self.pick.stop()
        self._stop_polling()
        if week_id in self.stores:
            # Seen already this run: show it as it was, and read what has changed since.
            self._opened((week_id, self.stores[week_id]))
            self._poll()
            self._poll_comments()  # which also sees whether the sheet has been deleted since
            return
        if self.store is None:
            self.welcome.show_working(f"Opening {week_id.title}")
            self.pages.setCurrentWidget(self.welcome)
        folder_id = self.state.folder_id
        self._submit("open", lambda: self._open(folder_id, week_id), f"Opening {week_id.title}...")

    def _open(self, folder_id: str, week_id: WeekId) -> tuple[WeekId, BoardStore | None]:
        """Read the week and nothing else, so the board is up as soon as it can be.

        The staff lists and the comments follow as quiet jobs of their own once it is.
        """
        sheet = self.workspace.open_week(folder_id, week_id, report=self.jobs.progress.emit)
        return week_id, None if sheet is None else BoardStore(self.workspace, sheet)

    def start_new_week(self) -> None:
        """Make a sheet for the week the toolbar is showing, from the template.

        Which week it is has already been said twice, in the toolbar and on the panel
        offering to make it, so it is not asked for a third time.
        """
        if self.workspace is None or not self.state.folder_id:
            self.link_folder()
            return
        week_id = WeekId(self.state.session, self.state.week)
        self.welcome.show_working(
            f"Creating {week_id.title}",
            "Writing the tabs and formatting them. This takes a few seconds.",
        )
        self.pages.setCurrentWidget(self.welcome)
        self._submit("create", lambda: self._create(week_id), f"Creating {week_id.title}...")

    def _create(self, week_id: WeekId) -> WeekId:
        seed = self.store.sheet if self.store is not None else None
        self.workspace.create_week(
            self.state.folder_id, week_id, seed, report=self.jobs.progress.emit
        )
        return week_id

    def edit_roster(self) -> None:
        """Add or rename cabins, then rebuild the board around them."""
        if self.store is None:
            return
        dialog = RosterDialog(self.store.week.cabins, self)
        if dialog.exec() != RosterDialog.Accepted or not dialog.cabins:
            return
        self.store.set_cabins(dialog.cabins)
        self._draw()
        self._push("Saving cabins...")

    def add_card(self, cabin: str, column: int) -> None:
        """Put a new card in an empty slot and open it for editing."""
        self._edit(cabin, column, CabinAct())

    def edit_card(self, card_id: str) -> None:
        """Open the editor for a card already on the board."""
        slot = self.store.week.locate(card_id) if self.store else None
        if slot is None:
            return
        self._edit(slot[0], slot[1], self.store.week.card(*slot))

    def _edit(self, cabin: str, column: int, card: CabinAct) -> None:
        """Zoom into the card's slot and open its fields there."""
        if self.store is None or self.zoom.is_open:
            return
        form = CardForm(
            card,
            f"{cabin} - {self._column_label(column)}",
            self.store.locations,
            self.store.staff,
        )
        self.editing = (cabin, column)
        self.board.reveal_slot(cabin, column)
        self.zoom.open(form, lambda: _content(self.board.slots.get((cabin, column))))

    def show_stats(self) -> None:
        """Open the week's statistics, on whichever measure was looked at last."""
        if self.store is None or self.zoom.is_open or self.stats_zoom.is_open:
            return
        button = self.board.stats_button
        panel = StatsPanel(button.measure.key)
        panel.measure_changed.connect(button.set_measure)
        panel.show_week(self.store.week)
        self.stats_zoom.open(panel, lambda: self.board.stats_button)

    def _save_edit(self, card: CabinAct | None) -> None:
        """Write what the open card now says, before the zoom back out lands on it."""
        if self.store is None or self.editing is None:
            return
        cabin, column = self.editing
        self.editing = None
        self.store.save_card(cabin, column, card)
        self.selected_card = card.id if card else None
        self._draw_slots([(cabin, column)])
        self._push("Saving card...")

    def swap_cards(self, cabin: str, one: int, other: int) -> None:
        """Exchange two cards in a cabin row."""
        if self.store is None or one == other:
            return
        self.store.swap(cabin, one, other)
        self._draw_slots([(cabin, one), (cabin, other)])
        self._push("Moving card...")

    def set_subtitle(self, column: int, text: str) -> None:
        """Name what else is happening on a weekday."""
        if self.store is None or self.store.week.days[column].subtitle == text.strip():
            return
        self.store.set_subtitle(column, text)
        self._push("Saving day...")

    def add_overflow(self) -> None:
        """Widen the unplaced zone."""
        if self.store is None:
            return
        self.store.add_overflow_column()
        self._draw()
        self._push("Widening the board...")

    def select_card(self, card_id: str) -> None:
        """Show one card's comments."""
        self.selected_card = card_id
        self.board.select(card_id)
        self._draw_comments()

    def add_comment(self, card_id: str, text: str) -> None:
        """Start a thread about a card."""
        if self.store is None:
            return
        self.store.add_comment(card_id, text)
        self._push_comment("Posting comment...")

    def reply_to_comment(self, comment_id: str, text: str) -> None:
        """Add a message to a thread."""
        if self.store is None:
            return
        self.store.reply(comment_id, text)
        self._push_comment("Posting reply...")

    def resolve_comment(self, comment_id: str) -> None:
        """Close a thread."""
        if self.store is None:
            return
        self.store.resolve(comment_id)
        self._push_comment("Resolving...")

    def _push_comment(self, message: str) -> None:
        """Send a comment change, and redraw once Google has it: only then is it real."""
        self.comments_pending = True
        self._push(message)

    def check_for_updates(self, quietly: bool = False) -> None:
        """Ask GitHub whether a newer Brain Waves has been published.

        Quietly, on startup: nothing is said unless there is something to say.
        """
        self._submit(
            "update-quiet" if quietly else "update-check",
            lambda: latest_release(self.config.releases_url),
            "" if quietly else "Checking for updates...",
        )

    def _install_update(self, release) -> None:
        answer = QMessageBox.question(
            self,
            "Update available",
            f"Brain Waves {release.version} is out. You have {__version__}.\n\n"
            f"{release.notes[:400]}\n\nDownload and install it now?",
        )
        if answer != QMessageBox.Yes:
            self._set_busy("")
            return
        self._submit(
            "update-install",
            lambda: install(download(release)),
            f"Downloading {release.version}...",
        )

    def _submit(self, name: str, work, message: str = "") -> None:
        """Send a job, and say so unless it is one of the quiet ones.

        A job already in flight under the same name is not sent twice, so a slow read
        cannot pile polls up behind it.
        """
        self.running.add(name)
        if name not in QUIET_JOBS:
            self.activity.show()
            if message:
                self._set_busy(message)
        self.jobs.submit(name, work)

    def _settle(self) -> None:
        """The queue has emptied: take the bar down."""
        self.running.clear()
        self.activity.hide()

    def _job_progress(self, message: str) -> None:
        """A long job saying which step it is on."""
        self._set_busy(message)
        if self.pages.currentWidget() is self.welcome:
            self.welcome.say(message)

    def _push(self, message: str) -> None:
        self._submit("flush", self.store.flush, message)

    def _poll(self) -> None:
        """Read the board again. Every time: see `brainwaves.store` for why."""
        if self.store is None or "sync" in self.running:
            return
        self._submit("sync", self.store.poll)

    def _poll_comments(self) -> None:
        """Read the comments, on their own slower beat."""
        if self.store is None or "comments" in self.running:
            return
        self._submit("comments", self.store.reload_comments)

    def refresh(self) -> None:
        """Read everything again now, whatever the revision says."""
        if self.store is None:
            return
        self._submit("reload", self.store.reload, "Reading the sheet...")

    def _stop_polling(self) -> None:
        self.poll.stop()
        self.comment_poll.stop()

    def _draw(self) -> None:
        """Draw the whole board. For opening a week, or a change of shape."""
        if self.store is None:
            return
        counts = binding.count_by_card(self.store.comments)
        self.board.show_week(self.store.week, counts, self.store.staff)
        self.board.select(self.selected_card)
        self._draw_alongside()
        self.pages.setCurrentWidget(self.board)

    def _draw_slots(self, slots) -> None:
        """Draw the slots a change touched, and nothing else. This is what a drag uses."""
        if self.store is None:
            return
        counts = binding.count_by_card(self.store.comments)
        self.board.refresh_slots(self.store.week, slots, counts, self.store.staff)
        self.board.select(self.selected_card)
        self._draw_alongside()

    def _draw_changes(self) -> None:
        """Draw whatever somebody else changed, and only that.

        A colleague moving one card should cost two slots here, not the whole board. The
        board knows the week it last drew, so the difference is there to be read; a card
        whose comment count has changed is redrawn too, to show the new count.
        """
        if self.store is None:
            return
        changed = _difference(self.board.week, self.store.week)
        if changed is None:
            self._draw()
            return
        counts, drawn = binding.count_by_card(self.store.comments), self.board.counts
        recounted = {
            slot
            for slot, card in self.store.week.cards.items()
            if counts.get(card.id) != drawn.get(card.id)
        }
        self._draw_slots(list({*changed, *recounted}))

    def _draw_alongside(self) -> None:
        """The panels beside the board, which are small enough to redraw either way."""
        self.conflicts.show_conflicts(find_conflicts(self.store.week, self.store.staff))
        self._draw_comments()
        if self.stats_zoom.is_open and not self.stats_zoom.closing:
            self.stats_zoom.form.show_week(self.store.week)

    def _draw_comments(self) -> None:
        if self.store is None:
            return
        slot = self.store.week.locate(self.selected_card) if self.selected_card else None
        card = self.store.week.card(*slot) if slot else None
        where = f"{slot[0]} - {self._column_label(slot[1])}" if slot else ""
        threads = (
            binding.for_card(self.store.comments, card.id)
            if card
            else binding.orphaned(self.store.comments, self.store.week)
        )
        self.comments.show_card(card, where, threads)

    def _column_label(self, column: int) -> str:
        if self.store is None:
            return ""
        if column < DAY_COLUMNS:
            return self.store.week.days[column].label
        return EXTRA

    def _say_offline(self, message: str) -> None:
        """Report a failed poll in the status line. It will be tried again in a moment."""
        self.status.setObjectName("statusError")
        self.status.setText(f"  Not reading Google just now: {message.splitlines()[0][:120]}")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _set_busy(self, message: str) -> None:
        self.status.setObjectName("statusBusy" if message else "status")
        self.status.setText(message or self._idle_text())
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _idle_text(self) -> str:
        if self.store is None:
            return ""
        return week_summary(self.store.week)

    def _job_done(self, name: str, result) -> None:
        self.running.discard(name)
        if name in {"comments", "reload"} and self._drop_gone():
            return
        if name == "signin":
            self._signed_in(result)
        elif name == "open":
            self._opened(result)
        elif name == "staff" and result:
            self._draw_heroes()
        elif name == "create":
            self._created(result)
        elif name in {"reload", "sync"} and result or name == "comments":
            self._draw_changes()
        elif name == "update-check":
            self._checked(result)
        elif name == "update-quiet" and result is not None:
            self._install_update(result)
        elif name == "update-install":
            QMessageBox.information(
                self, "Update installed", f"Restart Brain Waves to use it.\n\n{result}"
            )
        if name in {"flush", "reload", "update-check"}:
            self._set_busy("")
        if name == "reload" or (name == "flush" and self.comments_pending):
            self.comments_pending = False
            self._draw_changes()

    def _drop_gone(self) -> bool:
        """Forget every week whose sheet has been deleted. True if it was the one on show."""
        gone = [week_id for week_id, store in self.stores.items() if store.gone]
        for week_id in gone:
            del self.stores[week_id]
        if self.store is None or not self.store.gone:
            return False
        title = self.store.week.id.title
        self.zoom.dismiss()
        self.stats_zoom.dismiss()
        self.store = None
        self.selected_card = None
        self._stop_polling()
        self.sheet_label.setText("")
        self._show_welcome(
            f"{title} has been deleted from Google Drive.",
            "Start New Week",
            "If that was a mistake, restore it from the Drive trash and open the week again.",
        )
        return True

    def _draw_heroes(self) -> None:
        """Redraw the cards with HERO chips, which the staff lists have just said more about."""
        if self.store is None or self.pages.currentWidget() is not self.board:
            return
        slots = [slot for slot, card in self.store.week.cards.items() if card.heroes]
        self._draw_slots(slots)

    def _opened(self, result: tuple[WeekId, BoardStore | None]) -> None:
        week_id, store = result
        if week_id != WeekId(self.state.session, self.state.week):
            return  # the week was changed again while this one was being read
        if store is not self.store:
            self.zoom.dismiss()  # a card half-edited belongs to the week that has gone
        if store is None:
            self.store = None
            self.stats_zoom.dismiss()
            self.sheet_label.setText("")
            self._show_welcome(
                f"There is no sheet for {week_id} in "
                f"{self.state.folder_name or 'the linked folder'}.",
                "Start New Week",
                "Link to Google Sheets picks a different folder.",
            )
            return
        fresh = week_id not in self.stores
        self.stores[week_id] = store
        if fresh:
            self._submit("comments", store.reload_comments)
        if self.workspace.staff is None and "staff" not in self.running:
            self._submit("staff", self.workspace.load_staff)
        self.store = store
        self.selected_card = None
        self.sheet_label.setText(f"{store.workbook.title} - {self.state.folder_name}")
        self._draw()
        self._set_busy("")
        self.poll.start()
        self.comment_poll.start()
        if not self.checked_for_updates:
            self.checked_for_updates = True
            self.check_for_updates(quietly=True)

    def _created(self, week_id: WeekId) -> None:
        self.open_week()

    def _checked(self, release) -> None:
        if release is None:
            self._set_busy("")
            QMessageBox.information(
                self, "Up to date", f"Brain Waves {__version__} is the newest version."
            )
            return
        self._install_update(release)

    def _job_failed(self, name: str, message: str) -> None:
        self.running.discard(name)
        self.activity.hide()
        if name == "update-quiet":
            return  # a failed startup check is not worth interrupting anyone for
        if name in {"sync", "comments"}:
            self._say_offline(message)  # a timer must never raise a dialog at people
            return
        self._set_busy("")
        if name == "create" and "already" in message:
            QMessageBox.warning(self, "That week already exists", message)
            return
        titles = {
            "signin": "Could not sign in",
            "open": "Could not open the week",
            "create": "Could not create the week",
            "flush": "Could not save to Google Sheets",
            "reload": "Could not read Google Sheets",
        }
        QMessageBox.critical(self, titles.get(name, "Something went wrong"), message)


def _difference(drawn, current):
    """The slots that differ between two weeks, or None if the board's shape changed."""
    if drawn is None or drawn.cabins != current.cabins or drawn.columns != current.columns:
        return None
    if drawn.days != current.days:
        return None  # a subtitle lives in the heading, which a slot redraw would miss
    slots = set(drawn.cards) | set(current.cards)
    return [slot for slot in slots if drawn.cards.get(slot) != current.cards.get(slot)]


def _content(slot) -> QWidget | None:
    """What a slot is showing, card or empty outline, for a zoom to grow out of."""
    return slot.content if slot is not None else None


def _counter(value: int) -> QSpinBox:
    box = QSpinBox()
    box.setRange(1, 12)
    box.setValue(value)
    box.setFixedWidth(58)
    return box


def _button(text: str, handler) -> QPushButton:
    button = QPushButton(text)
    button.clicked.connect(handler)
    return button


def _stretch() -> QWidget:
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    return spacer
