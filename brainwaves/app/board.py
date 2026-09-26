"""The board: cabins down the side, days across the top, cards in between.

The day headings and the cabin column are separate scroll areas kept in step with the
board's own, so the week reads the same at column eight as it does at column one.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter
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
    board_bg,
    board_cross,
    restyle,
    village_pair,
)
from brainwaves.model import DAY_COLUMNS, EXTRA, Week
from brainwaves.sheets.staff import StaffLists

SLOT_WIDTH = CARD_WIDTH + 2 * SLOT_PADDING
SLOT_HEIGHT = CARD_HEIGHT + 2 * SLOT_PADDING
HEADER_HEIGHT = 68


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
        # The comment counts the cards were last drawn with.
        self.counts: dict[str, int] = {}
        self.cards: dict[str, CardWidget] = {}
        self.slots: dict[tuple[str, int], SlotWidget] = {}
        self.selected: str | None = None
        self.clashing: tuple[str, ...] = ()
        self.staff = StaffLists()
        # Each cabin's row on the board, for shading the row under the cursor.
        self.rows: dict[str, int] = {}
        # Whether a card is in the air, when only its row is shaded.
        self.dragging = False
        self.setObjectName("boardView")
        self.setAttribute(Qt.WA_StyledBackground, True)
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
        self.grid_body = Ground()
        self.grid = QGridLayout(self.grid_body)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(0)
        # Slots are a fixed size, so a board wider or taller than the week keeps the week
        # packed into its corner rather than spreading the spare room out between columns.
        self.grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
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

    def refresh_slots(self, week: Week, slots, comment_counts, staff=None) -> None:
        """Redraw only these slots, leaving the rest of the board alone.

        Moving a card changes two slots. Rebuilding all hundred and sixty-eight to show
        that takes a third of a second, which is exactly long enough to feel like the
        program is thinking about it.
        """
        self.week = week
        self.counts = comment_counts
        self.staff = staff or self.staff
        wanted = [(cabin, column) for cabin, column in slots if (cabin, column) in self.slots]
        if len(wanted) != len(list(slots)):
            self.show_week(week, comment_counts, staff)  # the board's shape changed
            return
        self.cards = {
            identifier: widget
            for identifier, widget in self.cards.items()
            if (widget.cabin, widget.column) not in wanted
        }
        for cabin, column in wanted:
            card = week.card(cabin, column)
            self.slots[cabin, column].show_card(
                self._card(cabin, column, card, comment_counts)
                if card
                else self._empty(cabin, column)
            )
        self._show_clashing()
        self.select(self.selected)

    def show_week(self, week: Week, comment_counts: dict[str, int], staff=None) -> None:
        """Draw the week from scratch. For a change of shape, not a change of content."""
        self.week = week
        self.counts = comment_counts
        self.staff = staff or self.staff
        self.cards.clear()
        self.slots.clear()
        _clear(self.header_body.layout())
        _clear(self.side_body.layout())
        _clear(self.grid)
        self._fill_header(week)
        self._fill_side(week)
        self._fill_grid(week, comment_counts)
        self.grid_body.width_in_slots = week.columns
        self.grid_body.height_in_slots = len(week.cabins)
        self.cross(None, None)
        self.select(self.selected)
        self._show_clashing()

    def cross(self, row: int | None, column: int | None) -> None:
        """Shade one row and one column of the board, headings included; None for neither."""
        self.grid_body.shade(row, column)
        self.header_body.shade(None, column)
        self.side_body.shade(row, None)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """The cursor has left the board: nothing is being read across or down.

        Picking a card up sends one of these too, as the drag takes the pointer, but the
        card's row stays shaded until it is put down.
        """
        super().leaveEvent(event)
        if not self.dragging:
            self.cross(None, None)

    def _hovered(self, cabin: str, column: int) -> None:
        if not self.dragging:
            self.cross(self.rows.get(cabin), column)

    def show_clash(self, card_ids) -> None:
        """Ring these cards in red until something else is chosen.

        The board is also scrolled to the first of them: a card marked somewhere off the
        side of the screen is no use to anyone.
        """
        self.clashing = tuple(card_ids)
        self._show_clashing()
        if self.clashing:
            self.reveal(self.clashing[0])

    def reveal(self, card_id: str) -> None:
        """Scroll until a card can be seen."""
        widget = self.cards.get(card_id)
        if widget is not None:
            self.board.ensureWidgetVisible(widget, SLOT_WIDTH // 2, SLOT_HEIGHT // 2)

    def reveal_slot(self, cabin: str, column: int) -> None:
        """Scroll until a slot, full or empty, can be seen whole."""
        slot = self.slots.get((cabin, column))
        if slot is not None:
            self.board.ensureWidgetVisible(slot, 0, 0)

    def _show_clashing(self) -> None:
        marked = set(self.clashing)
        for identifier, widget in self.cards.items():
            wanted = identifier in marked
            if widget.property("clash") != wanted:
                widget.setProperty("clash", wanted)
                restyle(widget)

    def _follow_board(self) -> None:
        """Put the heading strips back where the board is."""
        self.header.horizontalScrollBar().setValue(self.board.horizontalScrollBar().value())
        self.side.verticalScrollBar().setValue(self.board.verticalScrollBar().value())

    def select(self, card_id: str | None) -> None:
        """Ring one card and unring whichever was ringed before.

        Only those two are touched. Restyling every card on the board to change one ring
        is most of a frame's work for nothing.
        """
        self.selected = card_id if card_id in self.cards else None
        for widget in self.cards.values():
            wanted = widget.card.id == self.selected
            if widget.property("selected") != wanted:
                widget.set_selected(wanted)

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
        self.rows = {cabin.name: row for row, cabin in enumerate(week.cabins)}
        for row, cabin in enumerate(week.cabins):
            for column in range(week.columns):
                slot = SlotWidget(cabin.name, column)
                # Finished with the drag before the swap redraws the card that began it.
                slot.dropped.connect(self._drag_over)
                slot.dropped.connect(self.swap_requested)
                slot.hovered.connect(self._hovered)
                card = week.card(cabin.name, column)
                slot.show_card(
                    self._card(cabin.name, column, card, comment_counts)
                    if card
                    else self._empty(cabin.name, column)
                )
                self.grid.addWidget(slot, row, column)
                self.slots[cabin.name, column] = slot

    def _card(self, cabin: str, column: int, card, counts: dict[str, int]) -> CardWidget:
        widget = CardWidget(cabin, column, card, counts.get(card.id, 0), self.staff)
        widget.picked.connect(self.card_picked)
        widget.edit_requested.connect(self.card_edit)
        widget.drag_started.connect(self._offer_row)
        widget.drag_ended.connect(self._drag_over)
        self.cards[card.id] = widget
        return widget

    def _empty(self, cabin: str, column: int) -> AddCard:
        widget = AddCard()
        widget.clicked.connect(lambda: self.add_requested.emit(cabin, column))
        return widget

    def _offer_row(self, cabin: str) -> None:
        """Shade the row the card may be dropped into, which is the only one that may.

        It is the same band the cursor draws, held for the length of the drag, and without
        the column, to say the card moves only across.
        """
        self.dragging = True
        self.cross(self.rows.get(cabin), None)

    def _drag_over(self) -> None:
        """The card is down. The board says so itself, not the card, which a drop replaces."""
        if self.dragging:
            self.dragging = False
            self._cross_under_cursor()

    def _cross_under_cursor(self) -> None:
        """Shade wherever the card was put down, or nothing if it was put down elsewhere."""
        widget = QApplication.widgetAt(QCursor.pos())
        while widget is not None and not isinstance(widget, SlotWidget):
            widget = widget.parentWidget()
        if widget is not None and self.slots.get((widget.cabin, widget.column)) is widget:
            self.cross(self.rows.get(widget.cabin), widget.column)
        else:
            self.cross(None, None)


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


class Ground(QWidget):
    """What the board, or one of its heading strips, is drawn on.

    It paints the warm background itself, and the row and column under the cursor a shade
    deeper behind the slots. Painting a band is one repaint, where marking the slots it
    covers would restyle thirty widgets every time the cursor crossed into another.

    Rows and columns are the slots' own size and start at the top left, as every layout on
    the board is packed. `width_in_slots` and `height_in_slots` stop the bands at the edge
    of the week; left at zero, a band runs the whole way across or down.
    """

    def __init__(self) -> None:
        super().__init__()
        self.row: int | None = None
        self.column: int | None = None
        self.width_in_slots = 0
        self.height_in_slots = 0

    def shade(self, row: int | None, column: int | None) -> None:
        """Shade this row and this column; None for neither."""
        if (row, column) != (self.row, self.column):
            self.row, self.column = row, column
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """The background, then the bands."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(board_bg()))
        band = QColor(board_cross())
        if self.row is not None:
            width = self.width_in_slots * SLOT_WIDTH or self.width()
            painter.fillRect(0, self.row * SLOT_HEIGHT, width, SLOT_HEIGHT, band)
        if self.column is not None:
            height = self.height_in_slots * SLOT_HEIGHT or self.height()
            painter.fillRect(self.column * SLOT_WIDTH, 0, SLOT_WIDTH, height, band)


def _strip(orientation) -> tuple[Strip, Ground]:
    area = Strip()
    body = Ground()
    layout = QHBoxLayout(body) if orientation == Qt.Horizontal else QVBoxLayout(body)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignLeft if orientation == Qt.Horizontal else Qt.AlignTop)
    area.setWidget(body)
    return area, body


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
