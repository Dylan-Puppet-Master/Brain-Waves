"""A cabin act as it looks on the board, and the slot that holds it.

A card is dragged onto another slot in the same cabin row and the two exchange places,
which is the move the old spreadsheet took six steps to make.
"""

import shiboken6
from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from brainwaves.app.chips import describe
from brainwaves.app.theme import CARD_HEIGHT, CARD_WIDTH, SLOT_PADDING, restyle
from brainwaves.app.widgets import FlowLayout, chip, elided, risk_chip
from brainwaves.model import CabinAct
from brainwaves.sheets.staff import PERSON, StaffLists

MIME = "application/x-brainwaves-card"
TEXT_WIDTH = CARD_WIDTH - 24
HEADER_SPACING = 6
FLAGS = (
    ("van", "Van"),
    ("armory", "Armory"),
    ("picnic", "Picnic"),
    ("food", "Food"),
    ("level_two", "Level 2 on Ground"),
)


class CardWidget(QFrame):
    """One cabin act. Click to select, double-click to edit, drag to move."""

    picked = Signal(str)
    edit_requested = Signal(str)
    drag_started = Signal(str)
    drag_ended = Signal()

    def __init__(
        self, cabin: str, column: int, card: CabinAct, comments: int = 0, staff=None
    ) -> None:
        super().__init__()
        self.cabin = cabin
        self.column = column
        self.card = card
        self.staff = staff or StaffLists()
        self.setObjectName("card")
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(_tooltip(card))
        self._press: QPoint | None = None
        self._build(comments)

    def set_selected(self, selected: bool) -> None:
        """Ring the card while its comments are on show."""
        self.setProperty("selected", selected)
        restyle(self)

    def _build(self, comments: int) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        badges = [risk_chip(self.card.risk.value)]
        if comments:
            badges.append(chip(f"{comments}", "commentBadge", "Open comments"))
        header = QHBoxLayout()
        header.setSpacing(HEADER_SPACING)
        # The title gets whatever the badges beside it leave, measured rather than guessed,
        # so a long title is cut short instead of running underneath them.
        room = TEXT_WIDTH
        for badge in badges:
            badge.ensurePolished()
            room -= badge.sizeHint().width() + HEADER_SPACING
        title = QLabel()
        title.setObjectName("cardTitle")
        title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        elided(title, self.card.title or "Untitled", room, lines=2)
        header.addWidget(title, 1)
        for badge in badges:
            header.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(header)

        description = QLabel()
        description.setObjectName("cardDescription")
        elided(description, self.card.description, TEXT_WIDTH, lines=2)
        layout.addWidget(description)

        if self.card.location:
            location = QLabel()
            location.setObjectName("cardLocation")
            elided(location, self.card.location, TEXT_WIDTH)
            layout.addWidget(location)

        flags = [label for field, label in FLAGS if getattr(self.card, field)]
        if flags:
            layout.addWidget(_chip_bar(flags, "flagChip"))
        layout.addStretch(1)
        if self.card.heroes:
            layout.addWidget(self._hero_bar())

    def _hero_bar(self) -> QWidget:
        """The HERO chips, with a group asked for by name reading differently from a person."""
        bar = QWidget()
        layout = FlowLayout(bar)
        for text in self.card.heroes:
            kind = self.staff.kind_of(text)
            name = "chip" if kind == PERSON else "groupChip"
            layout.addWidget(chip(text, name, describe(text, self.staff)))
        return bar

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Remember where a drag would have started, and select the card."""
        if event.button() == Qt.LeftButton:
            self._press = event.position().toPoint()
            self.picked.emit(self.card.id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Open the editor."""
        self.edit_requested.emit(self.card.id)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Start dragging once the pointer has moved far enough to mean it."""
        if self._press is None or not (event.buttons() & Qt.LeftButton):
            return
        if (event.position().toPoint() - self._press).manhattanLength() < _threshold():
            return
        self._press = None
        self._drag()

    def _drag(self) -> None:
        data = QMimeData()
        data.setData(MIME, f"{self.cabin}|{self.column}".encode())
        drag = QDrag(self)
        drag.setMimeData(data)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, 24))
        self.setProperty("lifted", True)
        restyle(self)
        self.drag_started.emit(self.cabin)
        drag.exec(Qt.MoveAction)
        if not shiboken6.isValid(self):
            return  # dropped, and redrawn as a new card in the meantime
        self.setProperty("lifted", False)
        restyle(self)
        self.drag_ended.emit()


class AddCard(QFrame):
    """The dashed outline of a card that is not there yet."""

    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("addCard")
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Add a cabin act here")
        layout = QVBoxLayout(self)
        plus = QLabel("+")
        plus.setObjectName("cardEmpty")
        plus.setAlignment(Qt.AlignCenter)
        layout.addWidget(plus)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """A click asks for a new card."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class SlotWidget(QFrame):
    """One cabin's place on one day: a card, or room for one, and a drop target."""

    dropped = Signal(str, int, int)
    add_requested = Signal(str, int)
    hovered = Signal(str, int)

    def __init__(self, cabin: str, column: int) -> None:
        super().__init__()
        self.cabin = cabin
        self.column = column
        self.setObjectName("slot")
        self.setAcceptDrops(True)
        self.setFixedSize(CARD_WIDTH + 2 * SLOT_PADDING, CARD_HEIGHT + 2 * SLOT_PADDING)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*(SLOT_PADDING,) * 4)
        self.content: QWidget | None = None

    def show_card(self, widget: QWidget) -> None:
        """Put a card, or an empty outline, in the slot."""
        if self.content is not None:
            self._layout.removeWidget(self.content)
            self.content.deleteLater()
        self.content = widget
        self._layout.addWidget(widget)

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Say the cursor is over this cabin and day, for the board to shade them."""
        super().enterEvent(event)
        self.hovered.emit(self.cabin, self.column)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Take a card from this cabin's own row, and say so."""
        if not _from_cabin(event, self.cabin):
            event.ignore()
            return
        event.acceptProposedAction()
        self._highlight(True)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Stop saying so."""
        self._highlight(False)

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Exchange the dragged card with whatever is here."""
        self._highlight(False)
        source = _source(event)
        if source is None or source[0] != self.cabin:
            event.ignore()
            return
        event.acceptProposedAction()
        self.dropped.emit(self.cabin, source[1], self.column)

    def _highlight(self, on: bool) -> None:
        self.setProperty("hover", on)
        restyle(self)


def _chip_bar(labels, name: str) -> QWidget:
    bar = QWidget()
    layout = FlowLayout(bar)
    for text in labels:
        layout.addWidget(chip(text, name))
    return bar


def _tooltip(card: CabinAct) -> str:
    parts = [f"<b>{card.title or 'Untitled'}</b>"]
    for label, value in (
        ("", card.description),
        ("Materials", ", ".join(card.materials)),
        ("Location", card.location),
        ("Notes", card.notes),
        ("HEROES", ", ".join(card.heroes)),
    ):
        if value:
            parts.append(f"<b>{label}:</b> {value}" if label else value)
    return "<div style='max-width:320px'>" + "<br>".join(parts) + "</div>"


def _threshold() -> int:
    return QApplication.startDragDistance()


def _source(event) -> tuple[str, int] | None:
    data = event.mimeData()
    if not data.hasFormat(MIME):
        return None
    cabin, _, column = bytes(data.data(MIME)).decode().partition("|")
    return (cabin, int(column)) if column.isdigit() else None


def _from_cabin(event, cabin: str) -> bool:
    source = _source(event)
    return source is not None and source[0] == cabin
