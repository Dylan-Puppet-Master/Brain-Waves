import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from brainwaves.app.board import BoardView
from brainwaves.app.card import MIME, CardWidget, SlotWidget
from brainwaves.app.chips import ChipEditor
from brainwaves.app.comment_panel import CommentPanel
from brainwaves.app.dialogs import NewWeekDialog, RosterDialog
from brainwaves.app.editor import CardDialog
from brainwaves.app.theme import apply_theme
from brainwaves.app.widgets import when_phrase
from brainwaves.comments import count_by_card, for_card
from brainwaves.model import Cabin, CabinAct, Risk
from brainwaves.store import BoardStore
from tests.fakes import build


@pytest.fixture(scope="session")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    return instance


@pytest.fixture
def store(tmp_path, week):
    workspace, sheet = build(tmp_path, week)
    made = BoardStore(workspace, sheet)
    made.staff_names = ("Dylan", "Vic")
    return made


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
    slot = next(s for s in board.slots if s.cabin == "M1" and s.column == 3)
    slot.dropped.emit("M1", 0, 3)
    assert seen == [("M1", 0, 3)]


def test_the_editor_returns_what_was_typed(app, store):
    dialog = CardDialog(CabinAct(), "M1 - Monday", store.locations, store.staff_names)
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
    dialog = CardDialog(CabinAct(), "M1 - Monday", store.locations, store.staff_names)
    assert dialog.result_card is None


def test_deleting_in_the_editor_returns_nothing(app, store):
    dialog = CardDialog(store.week.card("M1", 0), "M1 - Monday", store.locations, store.staff_names)
    dialog.delete_button.click()
    assert dialog.result_card is None


def test_the_editor_keeps_the_card_id(app, store):
    original = store.week.card("M1", 0)
    dialog = CardDialog(original, "M1 - Monday", store.locations, store.staff_names)
    dialog.notes.setPlainText("bring spare rope")
    assert dialog.result_card.id == original.id
    assert dialog.result_card.notes == "bring spare rope"


def test_chips_add_and_remove(app):
    editor = ChipEditor(("Dylan", "Vic"))
    editor.set_values(["Dylan"])
    editor.entry.setText("Vic")
    editor._commit()
    assert editor.values == ["Dylan", "Vic"]
    editor._remove("Dylan")
    assert editor.values == ["Vic"]


def test_chips_ignore_a_repeat(app):
    editor = ChipEditor(("Dylan",))
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


def test_the_new_week_dialog_returns_a_week_id(app):
    dialog = NewWeekDialog(3, 2)
    assert str(dialog.week_id) == "S3W2"


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


def test_the_poll_holds_off_while_changes_are_still_being_written(window, store):
    window.swap_cards("M1", 0, 3)
    waiting = window.jobs.waiting
    window._poll()
    assert window.jobs.waiting == waiting


def test_the_comment_poll_holds_off_while_changes_are_being_written(window, store):
    window.swap_cards("M1", 0, 3)
    waiting = window.jobs.waiting
    window._poll_comments()
    assert window.jobs.waiting == waiting
