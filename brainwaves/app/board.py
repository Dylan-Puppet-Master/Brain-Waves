"""The board: cabins down the side, days across the top, cards in between.

The day headings and the cabin column are separate scroll areas kept in step with the
board's own, so the week reads the same at column eight as it does at column one.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from brainwaves.app.card import AddCard, CardWidget, SlotWidget
from brainwaves.app.theme import (
    CABIN_WIDTH,
    CARD_HEIGHT,
    CARD_WIDTH,
    SLOT_PADDING,
    restyle,
    village_pair,
)
from brainwaves.model import DAY_COLUMNS, EXTRA, Week

SLOT_WIDTH = CARD_WIDTH + 2 * SLOT_PADDING
SLOT_HEIGHT = CARD_HEIGHT + 2 * SLOT_PADDING
HEADER_HEIGHT = 68
BLINK_MILLISECONDS = 550


class BoardView(QWidget):
    """Every card in the week, arranged the way the villages think about them."""

    card_picked = Signal(str)
    card_edit = Signal(str)
    swap_requested = Signal(str, int, int)
    add_requested = Signal(str, int)
    subtitle_changed = Signal(int, str)
    overflow_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.week: Week | None = None
        self.cards: dict[str, CardWidget] = {}
        self.slots: list[SlotWidget] = []
        self.selected: str | None = None
        self.blinking: tuple[str, ...] = ()
        self._lit = False
        self._blink = QTimer(self)
        self._blink.setInterval(BLINK_MILLISECONDS)
        self._blink.timeout.connect(self._toggle)
        self._build()

    def _build(self) -> None:
        self.corner = QWidget()
        self.corner.setFixedSize(CABIN_WIDTH, HEADER_HEIGHT)
        self.header, self.header_body = _strip(Qt.Horizontal)
        self.header.setFixedHeight(HEADER_HEIGHT)
        self.side, self.side_body = _strip(Qt.Vertical)
        self.side.setFixedWidth(CABIN_WIDTH)
        self.board = QScrollArea()
        self.board.setWidgetResizable(True)
        self.grid_body = QWidget()
        self.grid = QGridLayout(self.grid_body)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(0)
        self.board.setWidget(self.grid_body)

        # The strips label the board, so they may only ever be where the board is. Scrolling
        # one of them directly — a wheel over it, or clicking a subtitle, which makes the
        # strip scroll to show what has focus — is corrected rather than merely discouraged.
        for bar in (
            self.board.horizontalScrollBar(),
            self.board.verticalScrollBar(),
            self.header.horizontalScrollBar(),
            self.side.verticalScrollBar(),
        ):
            bar.valueChanged.connect(self._follow_board)
        self.header.hand_wheel_to(self.board)
        self.side.hand_wheel_to(self.board)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        top.addWidget(self.corner)
        top.addWidget(self.header, 1)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(0)
        bottom.addWidget(self.side)
        bottom.addWidget(self.board, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(4)
        layout.addLayout(top)
        layout.addLayout(bottom, 1)

    def show_week(self, week: Week, comment_counts: dict[str, int]) -> None:
        """Draw the week from scratch. Cheap enough that nothing here is incremental."""
        self.week = week
        self.cards.clear()
        self.slots.clear()
        _clear(self.header_body.layout())
        _clear(self.side_body.layout())
        _clear(self.grid)
        self._fill_header(week)
        self._fill_side(week)
        self._fill_grid(week, comment_counts)
        self.select(self.selected)
        self._show_blinking()

    def blink(self, card_ids) -> None:
        """Ring these cards in red, on and off, until something else is chosen.

        The board is also scrolled to the first of them: a card blinking somewhere off the
        side of the screen is no use to anyone.
        """
        self.blinking = tuple(card_ids)
        self._lit = True
        self._show_blinking()
        if not self.blinking:
            self._blink.stop()
            return
        self._blink.start()
        self.reveal(self.blinking[0])

    def reveal(self, card_id: str) -> None:
        """Scroll until a card can be seen."""
        widget = self.cards.get(card_id)
        if widget is not None:
            self.board.ensureWidgetVisible(widget, SLOT_WIDTH // 2, SLOT_HEIGHT // 2)

    def _toggle(self) -> None:
        self._lit = not self._lit
        self._show_blinking()

    def _show_blinking(self) -> None:
        lit = set(self.blinking) if self._lit else set()
        for identifier, widget in self.cards.items():
            wanted = identifier in lit
            if widget.property("clash") != wanted:
                widget.setProperty("clash", wanted)
                restyle(widget)

    def _follow_board(self) -> None:
        """Put the heading strips back where the board is."""
        self.header.horizontalScrollBar().setValue(self.board.horizontalScrollBar().value())
        self.side.verticalScrollBar().setValue(self.board.verticalScrollBar().value())

    def select(self, card_id: str | None) -> None:
        """Ring one card and unring the rest."""
        self.selected = card_id if card_id in self.cards else None
        for identifier, widget in self.cards.items():
            widget.set_selected(identifier == self.selected)

    def _fill_header(self, week: Week) -> None:
        """Headings, as wide in total as the slots below them, so the two scroll together."""
        layout = self.header_body.layout()
        for column in range(week.columns):
            layout.addWidget(self._day_header(week, column))

    def _day_header(self, week: Week, column: int) -> QWidget:
        """One column heading, exactly as wide as the slots beneath it."""
        outer = QWidget()
        outer.setFixedSize(SLOT_WIDTH, HEADER_HEIGHT)
        frame = QVBoxLayout(outer)
        frame.setContentsMargins(SLOT_PADDING, 0, SLOT_PADDING, 6)
        holder = QWidget()
        holder.setObjectName("dayHeader")
        frame.addWidget(holder)
        box = QVBoxLayout(holder)
        box.setContentsMargins(12, 5, 12, 5)
        box.setSpacing(0)
        if column < DAY_COLUMNS:
            name = QLabel(week.days[column].name)
            name.setObjectName("dayName")
            subtitle = QLineEdit(week.days[column].subtitle)
            subtitle.setObjectName("daySubtitle")
            subtitle.setPlaceholderText("what else is on today?")
            subtitle.editingFinished.connect(
                lambda index=column, field=subtitle: self.subtitle_changed.emit(index, field.text())
            )
            box.addWidget(name)
            box.addWidget(subtitle)
            return outer
        holder.setProperty("weekend", True)
        name = QLabel(EXTRA)
        name.setObjectName("unplacedName")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(name)
        row.addStretch(1)
        if column == week.columns - 1:
            add = QPushButton("+")
            add.setObjectName("addColumn")
            add.setToolTip("Add another unplaced column")
            add.setFixedSize(22, 22)
            add.clicked.connect(self.overflow_requested)
            row.addWidget(add)
        box.addLayout(row)
        box.addStretch(1)
        return outer

    def _fill_side(self, week: Week) -> None:
        layout = self.side_body.layout()
        seen = set()
        for cabin in week.cabins:
            village = cabin.village.label if cabin.village else ""
            layout.addWidget(_cabin_tile(cabin, village not in seen))
            seen.add(village)
        layout.addStretch(1)

    def _fill_grid(self, week: Week, comment_counts: dict[str, int]) -> None:
        for row, cabin in enumerate(week.cabins):
            for column in range(week.columns):
                slot = SlotWidget(cabin.name, column)
                slot.dropped.connect(self.swap_requested)
                card = week.card(cabin.name, column)
                slot.show_card(
                    self._card(cabin.name, column, card, comment_counts)
                    if card
                    else self._empty(cabin.name, column)
                )
                self.grid.addWidget(slot, row, column)
                self.slots.append(slot)

    def _card(self, cabin: str, column: int, card, counts: dict[str, int]) -> CardWidget:
        widget = CardWidget(cabin, column, card, counts.get(card.id, 0))
        widget.picked.connect(self.card_picked)
        widget.edit_requested.connect(self.card_edit)
        widget.drag_started.connect(self._lift)
        widget.drag_ended.connect(self._settle)
        self.cards[card.id] = widget
        return widget

    def _empty(self, cabin: str, column: int) -> AddCard:
        widget = AddCard()
        widget.clicked.connect(lambda: self.add_requested.emit(cabin, column))
        return widget

    def _lift(self, cabin: str) -> None:
        for slot in self.slots:
            slot.set_muted(slot.cabin != cabin)

    def _settle(self) -> None:
        for slot in self.slots:
            slot.set_muted(False)


def _cabin_tile(cabin, first_of_village: bool) -> QWidget:
    """A cabin's label, exactly as tall as the row of slots beside it."""
    line, fill = village_pair(cabin.village.label if cabin.village else "")
    holder = QWidget()
    holder.setFixedSize(CABIN_WIDTH, SLOT_HEIGHT)
    outer = QVBoxLayout(holder)
    outer.setContentsMargins(0, SLOT_PADDING, SLOT_PADDING, SLOT_PADDING)
    tile = QFrame()
    tile.setObjectName("cabinTile")
    tile.setStyleSheet(f"#cabinTile {{ background: {fill}; }}")
    outer.addWidget(tile)
    layout = QVBoxLayout(tile)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(2)
    if first_of_village and cabin.village:
        village = QLabel(cabin.village.label.upper())
        village.setObjectName("sectionTitle")
        village.setStyleSheet(f"color: {line};")
        layout.addWidget(village)
    name = QLabel(cabin.name)
    name.setObjectName("cabinName")
    name.setStyleSheet(f"color: {line};")
    who = QLabel(cabin.label.partition(" - ")[2])
    who.setObjectName("cabinWho")
    who.setWordWrap(True)
    who.setStyleSheet(f"color: {line};")
    layout.addWidget(name)
    layout.addWidget(who)
    layout.addStretch(1)
    return holder


class Strip(QScrollArea):
    """A heading strip. It never scrolls itself; the board it labels scrolls it."""

    def __init__(self) -> None:
        super().__init__()
        self.partner: QScrollArea | None = None
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)

    def hand_wheel_to(self, partner: QScrollArea) -> None:
        """Send the wheel to the board, so scrolling over a heading scrolls the week."""
        self.partner = partner

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Scroll the board, never the strip."""
        if self.partner is not None:
            QApplication.sendEvent(self.partner.viewport(), event)
            return
        event.ignore()


def _strip(orientation) -> tuple[Strip, QWidget]:
    area = Strip()
    body = QWidget()
    layout = QHBoxLayout(body) if orientation == Qt.Horizontal else QVBoxLayout(body)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    area.setWidget(body)
    return area, body


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
