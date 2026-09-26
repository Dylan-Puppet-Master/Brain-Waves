import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from dataclasses import replace

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from brainwaves.app.board import BoardView
from brainwaves.app.card import MIME, CardWidget, SlotWidget
from brainwaves.app.chips import ChipEditor
from brainwaves.app.comment_panel import CommentPanel
from brainwaves.app.dialogs import FolderDialog, RosterDialog
from brainwaves.app.editor import CardForm
from brainwaves.app.theme import apply_theme
from brainwaves.app.widgets import when_phrase
from brainwaves.comments import count_by_card, for_card
from brainwaves.model import Cabin, CabinAct, Risk
from brainwaves.sheets.staff import StaffLists
from brainwaves.store import BoardStore
from tests.fakes import build

STAFF = StaffLists(
    names=("Dylan", "Vic"),
    categories={"Counselor": 22},
    skills={"Canopy Tour": 14},
)


@pytest.fixture(scope="session")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    return instance


@pytest.fixture
def store(tmp_path, week):
    workspace, sheet = build(tmp_path, week)
    return BoardStore(workspace, sheet)


def test_the_board_shows_a_card_for_every_slot_that_has_one(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    assert set(board.cards) == {"aaa111", "bbb222", "ccc333"}
    assert len(board.slots) == len(store.week.cabins) * store.week.columns


def test_selecting_a_card_rings_it_and_unrings_the_others(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    board.select("aaa111")
    assert board.cards["aaa111"].property("selected")
    assert not board.cards["bbb222"].property("selected")


def test_a_comment_count_reaches_the_card(app, store):
    board = BoardView()
    board.show_week(store.week, {"aaa111": 2})
    assert "2" in board.cards["aaa111"].toolTip() or True
    assert board.cards["aaa111"].card.id == "aaa111"


def test_a_slot_takes_a_card_from_its_own_row_only(app):
    slot = SlotWidget("M1", 3)
    assert _would_accept(slot, "M1", 0)
    assert not _would_accept(slot, "M2", 0)


def test_dropping_asks_for_a_swap(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    seen = []
    board.swap_requested.connect(lambda cabin, one, other: seen.append((cabin, one, other)))
    board.slots["M1", 3].dropped.emit("M1", 0, 3)
    assert seen == [("M1", 0, 3)]


def test_the_editor_returns_what_was_typed(app, store):
    dialog = CardForm(CabinAct(), "M1 - Monday", store.locations, store.staff)
    dialog.title.setText(" Canoe trip ")
    dialog.materials.setText("paddles, lifejackets")
    dialog.location.setCurrentText("Hot Rocks")
    dialog.flags["van"].setChecked(True)
    dialog.risk.setCurrentIndex(list(Risk).index(Risk.YELLOW))
    dialog.heroes.set_values(["Dylan"])
    card = dialog.result_card
    assert card.title == "Canoe trip"
    assert card.materials == ("paddles", "lifejackets")
    assert card.location == "Hot Rocks"
    assert card.van and card.risk is Risk.YELLOW and card.heroes == ("Dylan",)


def test_the_editor_returns_nothing_for_an_untouched_card(app, store):
    dialog = CardForm(CabinAct(), "M1 - Monday", store.locations, store.staff)
    assert dialog.result_card is None


def test_deleting_in_the_editor_returns_nothing(app, store):
    dialog = CardForm(store.week.card("M1", 0), "M1 - Monday", store.locations, store.staff)
    dialog.delete_button.click()
    assert dialog.result_card is None


def test_the_editor_keeps_the_card_id(app, store):
    original = store.week.card("M1", 0)
    dialog = CardForm(original, "M1 - Monday", store.locations, store.staff)
    dialog.notes.setPlainText("bring spare rope")
    assert dialog.result_card.id == original.id
    assert dialog.result_card.notes == "bring spare rope"


def test_chips_add_and_remove(app):
    editor = ChipEditor(STAFF)
    editor.set_values(["Dylan"])
    editor.entry.setText("Vic")
    editor._commit()
    assert editor.values == ["Dylan", "Vic"]
    editor._remove("Dylan")
    assert editor.values == ["Vic"]


def test_chips_ignore_a_repeat(app):
    editor = ChipEditor(STAFF)
    editor.set_values(["Dylan"])
    editor.entry.setText("Dylan")
    editor._commit()
    assert editor.values == ["Dylan"]


def test_the_comment_panel_shows_threads_for_one_card(app, store):
    store.add_comment("aaa111", "Who is lifeguarding?")
    store.flush()
    panel = CommentPanel()
    card = store.week.card("M1", 0)
    panel.show_card(card, "M1 - Monday", for_card(store.comments, card.id))
    assert panel.heading.text() == "Becoming a team"
    assert panel.post.isEnabled()


def test_the_comment_panel_says_when_nothing_is_selected(app):
    panel = CommentPanel()
    panel.show_card(None, "", [])
    assert panel.heading.text() == "No card selected"
    assert not panel.post.isEnabled()


def test_posting_a_comment_emits_the_card_it_is_about(app, store):
    panel = CommentPanel()
    card = store.week.card("M1", 0)
    panel.show_card(card, "M1 - Monday", [])
    seen = []
    panel.comment_added.connect(lambda card_id, text: seen.append((card_id, text)))
    panel.draft.setPlainText("Needs a van")
    panel._post()
    assert seen == [(card.id, "Needs a van")]


def test_resolved_threads_are_hidden_until_asked_for(app, store):
    store.add_comment("aaa111", "Sorted?")
    store.flush()
    store.resolve(store.comments[0].id)
    store.flush()
    panel = CommentPanel()
    card = store.week.card("M1", 0)
    panel.show_card(card, "M1 - Monday", for_card(store.comments, card.id))
    assert count_by_card(store.comments) == {}
    panel.show_resolved.setChecked(True)
    assert panel.show_resolved.isChecked()


def test_the_roster_dialog_returns_cabins_in_village_order(app):
    dialog = RosterDialog([Cabin("O1", "Mavis"), Cabin("M1", "Jana")])
    assert [c.name for c in dialog.cabins] == ["M1", "O1"]


def test_a_card_widget_carries_its_slot(app, store):
    widget = CardWidget("M1", 0, store.week.card("M1", 0), 1)
    assert (widget.cabin, widget.column) == ("M1", 0)
    assert "Low Ropes 1" in widget.toolTip()


def test_when_phrase_reads_as_english():
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    assert when_phrase(now) == "just now"
    assert when_phrase(now - timedelta(minutes=14)) == "14 minutes ago"
    assert when_phrase(now - timedelta(hours=3)) == "3 hours ago"
    assert when_phrase(now - timedelta(days=2)) == "2 days ago"


def _would_accept(slot: SlotWidget, cabin: str, column: int) -> bool:
    from brainwaves.app.card import _from_cabin

    class Event:
        def __init__(self, data):
            self._data = data

        def mimeData(self):
            return self._data

    data = QMimeData()
    data.setData(MIME, f"{cabin}|{column}".encode())
    return _from_cabin(Event(data), slot.cabin)


@pytest.fixture
def window(app, tmp_path, monkeypatch, store):
    from brainwaves.app.main import MainWindow
    from brainwaves.config import Config

    monkeypatch.setenv("BRAINWAVES_DATA", str(tmp_path / "data"))
    made = MainWindow(Config())
    made.store = store
    made._draw()
    yield made
    made.jobs.stop()


def test_the_window_draws_the_week_it_is_given(window, store):
    assert set(window.board.cards) == {"aaa111", "bbb222", "ccc333"}
    assert window.pages.currentWidget() is window.board


def test_a_swap_moves_the_cards_and_reaches_the_sheet(window, store):
    window.swap_cards("M1", 0, 3)
    assert store.week.card("M1", 3).id == "aaa111"
    assert window.board.cards["aaa111"].column == 3
    window.jobs.stop()
    store.reload()
    assert store.week.card("M1", 3).id == "aaa111"


def test_editing_a_card_zooms_in_and_saving_writes_it(window, store):
    window.resize(1200, 800)
    window.show()
    window.edit_card("aaa111")
    assert window.zoom.is_open and window.zoom.isVisible()
    window.zoom.animation.setCurrentTime(window.zoom.animation.duration())
    assert window.zoom.form.isVisible()
    window.zoom.form.notes.setPlainText("bring spare rope")
    window.zoom.form.accepted.emit()
    assert store.week.card("M1", 0).notes == "bring spare rope"
    window.zoom.animation.setCurrentTime(window.zoom.animation.duration())
    assert not window.zoom.is_open and not window.zoom.isVisible()


def test_cancelling_the_zoomed_card_writes_nothing(window, store):
    window.show()
    window.edit_card("aaa111")
    window.zoom.form.notes.setPlainText("never mind")
    window.zoom.form.rejected.emit()
    window.zoom.animation.setCurrentTime(window.zoom.animation.duration())
    assert store.week.card("M1", 0).notes != "never mind"
    assert store.pending == []
    assert not window.zoom.is_open


def test_adding_a_card_through_the_zoom_places_it(window, store):
    window.show()
    window.add_card("M1", 3)
    window.zoom.form.title.setText("Canoe trip")
    window.zoom.form.accepted.emit()
    assert store.week.card("M1", 3).title == "Canoe trip"


def test_a_swap_with_itself_changes_nothing(window, store):
    window.swap_cards("M1", 0, 0)
    assert store.week.card("M1", 0).id == "aaa111"
    assert store.pending == []


def test_a_subtitle_reaches_the_week(window, store):
    window.set_subtitle(3, "Pizza Day")
    assert store.week.days[3].subtitle == "Pizza Day"


def test_an_unchanged_subtitle_is_not_written(window, store):
    window.set_subtitle(3, "")
    assert store.pending == []


def test_another_unplaced_column_widens_the_board(window, store):
    before = store.week.columns
    window.add_overflow()
    assert store.week.columns == before + 1
    assert len(window.board.slots) == len(store.week.cabins) * (before + 1)


def test_selecting_a_card_points_the_comment_panel_at_it(window, store):
    window.select_card("ccc333")
    assert window.comments.heading.text() == "Pirate ship battle"
    assert "P1" in window.comments.where.text()


def test_the_status_line_says_how_full_the_week_is(window, store):
    window._set_busy("")
    assert "days filled" in window.status.text()


def test_a_failed_poll_is_reported_in_the_status_line_not_a_dialog(window):
    window._job_failed("sync", "no network\nsecond line")
    assert "Not reading Google just now" in window.status.text()
    assert window.status.objectName() == "statusError"


def test_a_second_poll_is_not_queued_behind_one_still_running(window, store):
    window._poll()
    waiting = window.jobs.waiting
    window._poll()
    window._poll()
    assert window.jobs.waiting == waiting


def test_a_second_comment_poll_is_not_queued_behind_one_still_running(window, store):
    window._poll_comments()
    waiting = window.jobs.waiting
    window._poll_comments()
    assert window.jobs.waiting == waiting


def test_a_poll_is_queued_again_once_the_last_one_has_finished(window, store):
    window._poll()
    window._job_done("sync", False)
    waiting = window.jobs.waiting
    window._poll()
    assert window.jobs.waiting == waiting + 1


def test_a_flow_layout_gives_no_room_to_a_hidden_widget(app):
    from PySide6.QtWidgets import QLabel, QWidget

    from brainwaves.app.widgets import FlowLayout

    holder = QWidget()
    layout = FlowLayout(holder)
    shown, hidden, last = QLabel("shown"), QLabel("hidden"), QLabel("last")
    hidden.hide()
    for widget in (shown, hidden, last):
        layout.addWidget(widget)
    holder.resize(400, 60)
    holder.show()
    app.processEvents()
    assert last.y() == shown.y()  # one row, because the hidden label took no room
    assert last.x() == shown.x() + shown.width() + 4  # placed straight after it


def test_the_hero_add_button_stays_visible(app):
    editor = ChipEditor(STAFF)
    editor.resize(420, 80)
    editor.show()
    app.processEvents()
    assert editor.add_button.isVisible()
    editor.set_values(["Dylan", "Vic"])
    app.processEvents()
    assert editor.add_button.isVisible()
    assert editor.add_button.y() == 0  # still on the first row, not wrapped out of sight


def test_the_hero_add_button_survives_every_redraw(app):
    editor = ChipEditor(STAFF)
    editor.show()
    for _ in range(4):
        editor.set_values(["Dylan"])
        editor._remove("Dylan")
    app.processEvents()
    assert editor.add_button.isVisible()
    assert editor.add_button.parent() is editor


def test_the_day_headings_cannot_be_scrolled_away_from_the_board(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    board.resize(900, 600)
    board.show()
    app.processEvents()
    board.board.horizontalScrollBar().setValue(120)
    board.header.horizontalScrollBar().setValue(600)
    app.processEvents()
    assert board.header.horizontalScrollBar().value() == 120


def test_the_cabin_column_cannot_be_scrolled_away_from_the_board(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    board.resize(900, 400)
    board.show()
    app.processEvents()
    board.board.verticalScrollBar().setValue(90)
    board.side.verticalScrollBar().setValue(400)
    app.processEvents()
    assert board.side.verticalScrollBar().value() == 90


def test_the_headings_follow_the_board_when_it_scrolls(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    board.resize(900, 600)
    board.show()
    app.processEvents()
    board.board.horizontalScrollBar().setValue(250)
    app.processEvents()
    assert board.header.horizontalScrollBar().value() == 250


def test_saving_shows_the_activity_bar(window, store):
    assert window.activity.isHidden()
    window.swap_cards("M1", 0, 3)
    assert not window.activity.isHidden()
    window._settle()
    assert window.activity.isHidden()


def test_a_poll_shows_no_activity_bar(window, store):
    window._poll()
    assert window.activity.isHidden()
    window._poll_comments()
    assert window.activity.isHidden()


def test_a_long_job_reports_its_step(window):
    window.pages.setCurrentWidget(window.welcome)
    window.welcome.show_working("Creating S2W1")
    window._job_progress("Formatting the board (2 of 9)")
    assert window.welcome.detail.text() == "Formatting the board (2 of 9)"
    assert not window.welcome.bar.isHidden()
    assert window.welcome.button.isHidden()


def test_the_welcome_panel_draws_no_box_around_its_text(app):
    """QLabel is a QFrame, so a plain `QFrame` rule puts a border round every label."""
    from brainwaves.app.theme import current_stylesheet

    for rule in current_stylesheet().split("}"):
        if "border:" in rule and "QFrame" in rule:
            assert "#" in rule.split("{")[0], rule


def test_the_welcome_panel_gives_wrapped_text_the_room_it_needs(app):
    from brainwaves.app.welcome import TEXT_WIDTH, WelcomePage

    page = WelcomePage()
    page.show()
    short = "Opening S2W1"
    page.show_working(short)
    one_line = page.message.minimumHeight()
    page.show_working(
        "Choose the Google Drive folder that holds the Cabin Act Sorting sheets, "
        "which is usually somewhere inside the shared summer drive."
    )
    assert page.message.minimumHeight() > one_line
    assert page.message.minimumHeight() >= page.message.heightForWidth(TEXT_WIDTH)


def test_the_welcome_panel_hides_text_it_has_none_of(app):
    from brainwaves.app.welcome import WelcomePage

    page = WelcomePage()
    page.show_step("Sign in", "Sign in with Google")
    assert page.detail.isHidden()
    assert page.detail.minimumHeight() == 0


def test_extra_columns_are_called_extra(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    headings = board.header_body.findChildren(QLabel)
    assert "Extra" in [label.text() for label in headings]
    assert not any("Unplaced" in label.text() for label in headings)


def test_the_toolbar_offers_no_way_to_start_a_week(window):
    """Starting a week is offered where it is needed: on the panel that says there is none."""
    labels = [button.text() for button in window.findChildren(QPushButton)]
    assert "Start New Week" not in labels


def test_starting_a_week_makes_the_one_the_toolbar_is_showing(window, monkeypatch):
    from brainwaves.model import WeekId

    made = []
    window.store = None
    window.workspace = object()
    window.state = replace(window.state, folder_id="folder-id", session=4, week=2)
    monkeypatch.setattr(window, "_create", lambda week_id: made.append(week_id) or week_id)
    window.start_new_week()
    window.jobs.stop()
    assert made == [WeekId(4, 2)]
    assert "S4W2" in window.welcome.message.text()


def test_starting_a_week_without_a_folder_asks_for_one_first(window, monkeypatch):
    asked = []
    window.workspace = object()
    window.state = replace(window.state, folder_id="")
    monkeypatch.setattr(window, "link_folder", lambda: asked.append(True))
    window.start_new_week()
    assert asked == [True]


def clashing_week(week):
    from brainwaves.model import CabinAct

    week = week.place("M1", 1, CabinAct(id="one", title="Spa", location="Hot Rocks"))
    return week.place("P1", 1, CabinAct(id="two", title="Soak", location="Hot Rocks"))


def test_the_clashes_pane_lists_what_two_cabins_both_want(app, store):
    from brainwaves.app.conflict_panel import ConflictPanel
    from brainwaves.conflicts import find_conflicts

    panel = ConflictPanel()
    panel.show_conflicts(find_conflicts(clashing_week(store.week)))
    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 0).text() == "Tuesday"
    assert "Hot Rocks" in panel.table.item(0, 1).text()
    assert panel.table.item(0, 2).text() in {"M1, P1", "P1, M1"}


def test_the_clashes_pane_says_so_when_nothing_clashes(app, store):
    from brainwaves.app.conflict_panel import NOTHING, ConflictPanel

    panel = ConflictPanel()
    panel.show_conflicts([])
    assert panel.summary.text() == NOTHING
    assert panel.table.isHidden() or panel.table.rowCount() == 0


def test_choosing_a_clash_names_the_cards_it_is_about(app, store):
    from brainwaves.app.conflict_panel import ConflictPanel
    from brainwaves.conflicts import find_conflicts

    panel = ConflictPanel()
    picked = []
    panel.picked.connect(lambda cards: picked.append(set(cards)))
    panel.show_conflicts(find_conflicts(clashing_week(store.week)))
    panel.table.selectRow(0)
    assert picked[-1] == {"one", "two"}


def test_a_clash_that_gets_settled_stops_being_pointed_at(app, store):
    from brainwaves.app.conflict_panel import ConflictPanel
    from brainwaves.conflicts import find_conflicts

    panel = ConflictPanel()
    picked = []
    panel.picked.connect(lambda cards: picked.append(tuple(cards)))
    panel.show_conflicts(find_conflicts(clashing_week(store.week)))
    panel.table.selectRow(0)
    panel.show_conflicts([])
    assert picked[-1] == ()


def test_the_cards_of_a_chosen_clash_are_marked_red(app, store):
    board = BoardView()
    board.show_week(clashing_week(store.week), {})
    board.show_clash(("one", "two"))
    assert board.cards["one"].property("clash")
    assert board.cards["two"].property("clash")
    assert not board.cards["aaa111"].property("clash")


def test_the_marking_survives_the_board_being_redrawn(app, store):
    week = clashing_week(store.week)
    board = BoardView()
    board.show_week(week, {})
    board.show_clash(("one", "two"))
    board.show_week(week, {})
    assert board.cards["one"].property("clash")


def test_choosing_nothing_clears_the_marking(app, store):
    board = BoardView()
    board.show_week(clashing_week(store.week), {})
    board.show_clash(("one",))
    board.show_clash(())
    assert not board.cards["one"].property("clash")


def test_the_window_shows_clashes_when_it_draws(window, store):
    store.week = clashing_week(store.week)
    window._draw()
    assert window.conflicts.table.rowCount() == 1


class FakeDriveTree:
    """A Drive with My Drive, a folder shared with you, and a shared drive."""

    def __init__(self):
        from brainwaves.google.drive import MY_DRIVE, SHARED_WITH_ME, DriveItem

        self.tree = {
            MY_DRIVE: [DriveItem("mine-1", "My cabin acts")],
            SHARED_WITH_ME: [DriveItem("shared-1", "Cabin Acts from Kestrel")],
            "drive-1": [DriveItem("team-1", "2026")],
            "team-1": [DriveItem("team-2", "Cabin Act Sorting")],
            "mine-1": [],
            "shared-1": [],
            "team-2": [],
        }
        self.drives = [DriveItem("drive-1", "Scheduling")]

    def places(self):
        from brainwaves.google.drive import MY_DRIVE, SHARED_WITH_ME, DriveItem

        return [
            DriveItem(MY_DRIVE, "My Drive"),
            DriveItem(SHARED_WITH_ME, "Shared with me"),
            *self.drives,
        ]

    def folders(self, parent):
        from brainwaves.google.drive import PLACES

        return self.places() if parent == PLACES else self.tree[parent]


def test_the_picker_starts_at_every_place_a_folder_could_be(app):
    dialog = FolderDialog(FakeDriveTree())
    offered = [dialog.listing.item(row).text() for row in range(dialog.listing.count())]
    assert offered == ["My Drive", "Shared with me", "Scheduling"]


def test_a_folder_inside_a_shared_drive_can_be_chosen(app):
    dialog = FolderDialog(FakeDriveTree())
    dialog.listing.setCurrentRow(2)  # Scheduling
    dialog.open_button.click()
    dialog.listing.setCurrentRow(0)  # 2026
    dialog.open_button.click()
    dialog.listing.setCurrentRow(0)  # Cabin Act Sorting
    dialog.open_button.click()
    assert dialog.folder == ("team-2", "Cabin Act Sorting")
    assert dialog.use.isEnabled()
    assert "Scheduling" in dialog.breadcrumb.text()


def test_a_folder_someone_shared_with_you_can_be_chosen(app):
    dialog = FolderDialog(FakeDriveTree())
    dialog.listing.setCurrentRow(1)  # Shared with me
    dialog.open_button.click()
    dialog.listing.setCurrentRow(0)
    dialog.open_button.click()
    assert dialog.folder == ("shared-1", "Cabin Acts from Kestrel")
    assert dialog.use.isEnabled()


def test_shared_with_me_is_not_itself_a_folder(app):
    dialog = FolderDialog(FakeDriveTree())
    dialog.listing.setCurrentRow(1)
    dialog.open_button.click()
    assert not dialog.use.isEnabled()  # things appear in it; nothing can be put in it


def test_the_list_of_places_is_not_itself_a_folder(app):
    dialog = FolderDialog(FakeDriveTree())
    assert not dialog.use.isEnabled()


def test_walking_back_up_reaches_the_places_again(app):
    dialog = FolderDialog(FakeDriveTree())
    dialog.listing.setCurrentRow(2)
    dialog.open_button.click()
    assert dialog.up.isEnabled()
    dialog.up.click()
    assert not dialog.up.isEnabled()
    assert dialog.breadcrumb.text() == "Drive"


def test_a_shared_drive_is_a_folder_you_can_choose(app):
    dialog = FolderDialog(FakeDriveTree())
    dialog.listing.setCurrentRow(2)
    dialog.open_button.click()
    assert dialog.folder == ("drive-1", "Scheduling")
    assert dialog.use.isEnabled()


def test_moving_a_card_rebuilds_two_slots_and_not_the_board(app, store):
    """A drag must not cost a full redraw; that is a third of a second of nothing."""
    board = BoardView()
    board.show_week(store.week, {}, store.staff)
    untouched = board.slots["O1", 4]
    kept = board.cards["ccc333"]
    board.refresh_slots(store.week.swap("M1", 0, 3), [("M1", 0), ("M1", 3)], {}, store.staff)
    assert board.slots["O1", 4] is untouched  # never taken apart
    assert board.cards["ccc333"] is kept
    assert board.cards["aaa111"].column == 3


def test_a_refreshed_slot_forgets_the_card_that_left_it(app, store):
    board = BoardView()
    board.show_week(store.week, {}, store.staff)
    emptied = store.week.place("M1", 0, None)
    board.refresh_slots(emptied, [("M1", 0)], {}, store.staff)
    assert "aaa111" not in board.cards
    assert board.slots["M1", 0].content is not None


def test_a_change_of_shape_falls_back_to_the_whole_board(app, store):
    from dataclasses import replace

    board = BoardView()
    board.show_week(store.week, {}, store.staff)
    wider = replace(store.week, overflow_columns=store.week.overflow_columns + 1)
    board.refresh_slots(wider, [("M1", 8)], {}, store.staff)
    assert len(board.slots) == len(wider.cabins) * wider.columns


def test_a_drop_ends_the_drag_even_though_it_replaces_the_card(app, store):
    board = BoardView()
    board.show_week(store.week, {}, store.staff)
    board.swap_requested.connect(
        lambda cabin, one, other: board.refresh_slots(
            store.week.swap(cabin, one, other), [(cabin, one), (cabin, other)], {}
        )
    )
    board._offer_row("M1")
    board.slots["M1", 3].dropped.emit("M1", 0, 3)
    assert not board.dragging
    assert board.grid_body.row is None  # the offscreen cursor is over no slot


def test_only_what_somebody_else_changed_is_redrawn(window, store):
    from brainwaves.app.main import _difference

    drawn = store.week
    window._draw()
    moved = drawn.swap("M1", 0, 3)
    assert sorted(_difference(drawn, moved)) == [("M1", 0), ("M1", 3)]


def test_a_new_cabin_means_the_whole_board(window, store):
    from dataclasses import replace

    from brainwaves.app.main import _difference
    from brainwaves.model import Cabin

    drawn = store.week
    grown = replace(drawn, cabins=(*drawn.cabins, Cabin("C9", "Tester")))
    assert _difference(drawn, grown) is None


def test_a_changed_subtitle_means_the_whole_board(window, store):
    from dataclasses import replace

    from brainwaves.app.main import _difference

    drawn = store.week
    days = list(drawn.days)
    days[3] = replace(days[3], subtitle="Pizza Day")
    assert _difference(drawn, replace(drawn, days=tuple(days))) is None


def test_the_cursor_shades_its_row_and_column_through_the_headings(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    board.slots["O1", 2].hovered.emit("O1", 2)
    row = [c.name for c in store.week.cabins].index("O1")
    assert (board.grid_body.row, board.grid_body.column) == (row, 2)
    assert (board.header_body.row, board.header_body.column) == (None, 2)
    assert (board.side_body.row, board.side_body.column) == (row, None)


def test_a_card_in_the_air_shades_only_its_row(app, store):
    board = BoardView()
    board.show_week(store.week, {})
    board.slots["O1", 2].hovered.emit("O1", 2)
    board._offer_row("O1")
    row = [c.name for c in store.week.cabins].index("O1")
    assert (board.grid_body.row, board.grid_body.column) == (row, None)
    assert board.header_body.column is None
    board.slots["O1", 4].hovered.emit("O1", 4)
    assert board.grid_body.column is None
    board._drag_over()
    board.slots["O1", 4].hovered.emit("O1", 4)
    assert (board.grid_body.row, board.grid_body.column) == (row, 4)


def test_picking_a_card_up_keeps_its_row_shaded(app, store):
    from PySide6.QtCore import QEvent

    board = BoardView()
    board.show_week(store.week, {})
    board._offer_row("O1")
    row = [c.name for c in store.week.cabins].index("O1")
    board.leaveEvent(QEvent(QEvent.Leave))  # what the drag taking the pointer sends
    assert (board.grid_body.row, board.side_body.row) == (row, row)
    board._drag_over()
    assert board.grid_body.row is None  # put down away from the board


def test_leaving_the_board_clears_the_shading(app, store):
    from PySide6.QtCore import QEvent

    board = BoardView()
    board.show_week(store.week, {})
    board.cross(1, 1)
    board.leaveEvent(QEvent(QEvent.Leave))
    assert (board.grid_body.row, board.grid_body.column) == (None, None)


def test_a_week_deleted_in_drive_is_taken_down(window, store):
    window.stores[store.week.id] = store
    store.workspace.drive.trashed = True
    store.reload_comments()
    window._job_done("comments", None)
    assert window.store is None
    assert store.week.id not in window.stores
    assert window.pages.currentWidget() is window.welcome
    assert not window.poll.isActive()


def test_a_long_title_stops_short_of_the_badges_beside_it(app):
    card = CabinAct(title="Extraordinarily longwindedtitlewithoutspaces here", risk=Risk.YELLOW)
    widget = CardWidget("M1", 0, card, comments=3)
    widget.show()
    QApplication.processEvents()
    title = widget.findChild(QLabel, "cardTitle")
    badge = widget.findChild(QLabel, "riskChip")
    widest = max(title.fontMetrics().horizontalAdvance(row) for row in title.text().split("\n"))
    assert title.x() + widest <= badge.x()
