"""The card editor: the card itself, zoomed up until its fields can be typed into.

Opening a card flies the board towards it, the way a camera would, until the card fills the
middle of the board and its fields are there to edit. Closing flies back out to wherever the
card now sits. Nothing floats over the rest of the window: the comments and the toolbar stay
where they were. The week's statistics open the same way, out of the corner of the board.
"""

from dataclasses import replace

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSizeF,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from brainwaves.app.chips import ChipEditor
from brainwaves.app.theme import board_bg, risk_color, surface
from brainwaves.model import CabinAct, Risk
from brainwaves.names import join_list, split_list
from brainwaves.palette import RISK_LABELS

FLAGS = (
    ("van", "Van needed"),
    ("armory", "Armory"),
    ("picnic", "Picnic"),
    ("food", "Food (not a picnic)"),
    ("level_two", "Level 2 on Ground"),
)

ZOOM_MS = 320
# How far the open card stays from the edges of the board, and how wide it may grow.
MARGIN = 36
MAX_WIDTH = 800
# How much the board behind the open card is dimmed, at most, and how far the board itself
# is magnified: the card flies all the way up, but the board past it only so far, or it
# becomes a few enormous grey shapes.
DIM = 0.5
BOARD_ZOOM = 1.25
# The board goes out of focus as the card comes into it, by a Gaussian blur this wide in
# screen pixels. It is worked out once, at full resolution, on the board as it looks fully
# zoomed, so the blur that ends up on screen is never itself enlarged.
BLUR_RADIUS = 14
# How far into the zoom the blur starts to show. The blurred board covers only what can be
# seen from here on, which keeps it quick to make.
BLUR_FROM = 0.3
# The face the zoom grows out of fades into the open form between these magnifications.
FADE_FROM = 1.3
FADE_TO = 2.6


class CardForm(QFrame):
    """The fields of one cabin act, laid out as a big version of the card they make.

    Save or Delete emits `accepted`, after which `result_card` says what to write; Cancel
    emits `rejected`.
    """

    accepted = Signal()
    rejected = Signal()

    def __init__(self, card: CabinAct, where: str, locations, staff=None, parent=None) -> None:
        super().__init__(parent)
        self.card = card
        self.deleted = False
        self.setObjectName("cardEditor")
        self.setMaximumWidth(MAX_WIDTH)

        where_label = QLabel(where.upper())
        where_label.setObjectName("sectionTitle")
        self.title = QLineEdit(card.title)
        self.title.setObjectName("editorTitle")
        self.title.setPlaceholderText("What the cabin is doing")
        self.risk = _risk_box(card.risk)
        self.description = QTextEdit(card.description)
        self.description.setPlaceholderText("What happens, in a sentence or two")
        self.description.setFixedHeight(72)
        self.materials = QLineEdit(join_list(card.materials))
        self.materials.setPlaceholderText("comma separated")
        self.location = _location_box(locations, card.location)
        self.notes = QTextEdit(card.notes)
        self.notes.setFixedHeight(72)
        self.flags = {field: QCheckBox(label) for field, label in FLAGS}
        for field, box in self.flags.items():
            box.setChecked(getattr(card, field))
        self.heroes = ChipEditor(staff)
        self.heroes.set_values(card.heroes)
        self.setFocusProxy(self.title)

        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(self.title, 1)
        header.addWidget(self.risk, 0, Qt.AlignVCenter)

        left = QVBoxLayout()
        left.setSpacing(6)
        for label, field in (
            ("LOCATION", self.location),
            ("MATERIALS", self.materials),
            ("NOTES", self.notes),
        ):
            left.addWidget(_caption(label))
            left.addWidget(field)
        left.addStretch(1)
        right = QVBoxLayout()
        right.setSpacing(6)
        right.addWidget(_caption("NEEDS"))
        right.addWidget(_flag_grid(self.flags))
        right.addSpacing(6)
        right.addWidget(_caption("HEROES"))
        right.addWidget(self.heroes)
        hint = QLabel(
            "A HERO can be a person by name, a category of person, or a skill — anyone "
            "checked off on it will do."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        right.addWidget(hint)
        right.addStretch(1)
        columns = QHBoxLayout()
        columns.setSpacing(24)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("danger")
        self.delete_button.clicked.connect(self._delete)
        cancel = QPushButton("Cancel")
        cancel.setToolTip("Esc")
        cancel.clicked.connect(self.rejected)
        save = QPushButton("Save")
        save.setObjectName("primary")
        save.setToolTip("Ctrl+Enter")
        save.clicked.connect(self.accepted)
        buttons = QHBoxLayout()
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)
        layout.addWidget(where_label)
        layout.addLayout(header)
        layout.addWidget(self.description)
        layout.addLayout(columns, 1)
        layout.addLayout(buttons)

        for keys in ("Ctrl+Return", "Ctrl+Enter"):
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.accepted)
        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.rejected)

    @property
    def result_card(self) -> CabinAct | None:
        """The edited card, or None if it was deleted or left blank."""
        if self.deleted:
            return None
        edited = replace(
            self.card,
            title=self.title.text().strip(),
            description=self.description.toPlainText().strip(),
            materials=split_list(self.materials.text()),
            location=self.location.currentText().strip(),
            notes=self.notes.toPlainText().strip(),
            risk=Risk(self.risk.currentData()),
            heroes=tuple(self.heroes.values),
            **{field: box.isChecked() for field, box in self.flags.items()},
        )
        return None if edited.is_blank else edited

    @property
    def changed(self) -> bool:
        """Whether anything has been typed that closing without saving would lose."""
        return self.result_card != (None if self.card.is_blank else self.card)

    def _delete(self) -> None:
        self.deleted = True
        self.accepted.emit()


class CardZoom(QWidget):
    """Lies over the board and zooms into one card to edit it, then back out.

    `open` takes the form and a function that finds the widget the form grows out of: the
    card, or the empty outline of one. It is looked for again on the way out, because
    saving may have redrawn it. `saved` carries the result the moment Save or Delete is
    pressed, before the zoom back out, so whoever writes it can redraw the slot and the zoom
    lands on the card as it now is.

    Any sheet with a `rejected` signal can be zoomed into this way; `accepted`, `changed`
    and `result_card` are the card editor's alone. A sheet as wide as it likes, and
    vertically expanding, fills the board less the margin.
    """

    saved = Signal(object)

    def __init__(self, board: QWidget) -> None:
        super().__init__(board)
        self.board = board
        self.form: CardForm | None = None
        self.locate = lambda: None
        self.backdrop = QPixmap()
        self.blurred = QImage()
        self.blur_area = QRectF()
        self.face = QPixmap()  # the card as it sits on the board
        self.sheet = QPixmap()  # the open form, for drawing while it is still moving
        self.origin = QRectF()
        self.progress = 0.0
        self.closing = False
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(ZOOM_MS)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.valueChanged.connect(self._step)
        self.animation.finished.connect(self._landed)
        board.installEventFilter(self)
        self.hide()

    @property
    def is_open(self) -> bool:
        """Whether a card is being edited, or is on its way in or out."""
        return self.form is not None

    def open(self, form: CardForm, locate) -> None:
        """Zoom into the slot `locate` finds, and put the form there."""
        self.dismiss()
        self.form = form
        self.locate = locate
        form.setParent(self)
        form.hide()
        if hasattr(form, "accepted"):
            form.accepted.connect(self._save)
        form.rejected.connect(self.close_card)
        self.setGeometry(self.board.rect())
        self._snapshot()
        self._place_form()
        self.sheet = form.grab()
        self.closing = False
        self.show()
        self.raise_()
        self._run(0.0, 1.0)

    def close_card(self) -> None:
        """Zoom back out to the card's slot."""
        if self.form is None or self.closing:
            return
        self.closing = True
        self.sheet = self.form.grab()
        self.form.hide()
        self.hide()  # out of the way of the picture of the board
        self._snapshot()
        self.show()
        self.board.setFocus()
        self._run(self.progress, 0.0)

    def dismiss(self) -> None:
        """Go at once, without saving: the week behind the card has gone."""
        self.animation.stop()
        if self.form is not None:
            self.form.deleteLater()
        self.form = None
        self.closing = False
        self.progress = 0.0
        self.hide()

    def _save(self) -> None:
        if self.form is None or self.closing:
            return
        self.saved.emit(self.form.result_card)
        self.close_card()

    def _run(self, start: float, end: float) -> None:
        self.animation.stop()
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.setDuration(max(1, int(ZOOM_MS * abs(end - start))))
        self.animation.start()

    def _step(self, value) -> None:
        self.progress = float(value)
        self.update()

    def _landed(self) -> None:
        if self.closing:
            self.dismiss()
            return
        if self.form is not None:
            self.form.show()
            self.form.setFocus()

    def _snapshot(self) -> None:
        """Take the board as it looks, the card in it, and where the card is on it."""
        self.backdrop = self.board.grab()
        origin = self.locate()
        if origin is None:  # redrawn away: fly out to the middle of the board instead
            centre = QPointF(self.rect().center())
            self.face = QPixmap()
            self.origin = QRectF(centre, centre).adjusted(-40, -30, 40, 30)
            self._focus()
            return
        holder = origin.parentWidget()
        if holder is not None and holder.layout() is not None:
            holder.layout().activate()  # a card just redrawn has not been put in place yet
        self.face = origin.grab()
        self.origin = QRectF(QRect(origin.mapTo(self.board, QPoint(0, 0)), origin.size()))
        self._focus()

    def _target(self) -> QRectF:
        """Where the open card sits: the middle of the board, as large as it comfortably fits."""
        area = QRectF(self.rect()).adjusted(MARGIN, MARGIN, -MARGIN, -MARGIN)
        width, wanted = area.width(), area.height()
        if self.form is not None:
            width = min(width, self.form.maximumWidth())
            if self.form.sizePolicy().verticalPolicy() != QSizePolicy.Expanding:
                wanted = self.form.sizeHint().height()
        height = min(area.height(), wanted)
        return QRectF(0, 0, width, height).translated(
            area.center() - QPointF(width / 2, height / 2)
        )

    def _place_form(self) -> None:
        if self.form is None:
            return
        self.form.setGeometry(self._target().toRect())
        if self.form.layout() is not None:
            self.form.layout().activate()

    def _focus(self) -> None:
        """Blur the board at its fully zoomed size, so it meets the screen pixel for pixel.

        Only the part of the board in view once the blur starts to show is blurred:
        `blur_area` is that part, in the board's own coordinates.
        """
        ratio = self.backdrop.devicePixelRatio()
        _, scale = self._camera(1.0)
        area = self._in_view(BLUR_FROM).united(self._in_view(1.0)).adjusted(-8, -8, 8, 8)
        self.blur_area = area.intersected(
            QRectF(QPointF(0, 0), self.backdrop.deviceIndependentSize())
        )
        frame = QImage(
            (self.blur_area.size() * scale * ratio).toSize(), QImage.Format_ARGB32_Premultiplied
        )
        frame.setDevicePixelRatio(ratio)
        frame.fill(QColor(board_bg()))
        painter = QPainter(frame)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.scale(scale, scale)
        painter.translate(-self.blur_area.topLeft())
        painter.drawPixmap(QPointF(0, 0), self.backdrop)
        painter.end()
        self.blurred = _blurred(frame, round(BLUR_RADIUS * ratio))

    def _in_view(self, progress: float) -> QRectF:
        """The part of the board on screen at this point in the zoom."""
        shift, scale = self._camera(progress)
        return QRectF(-shift / scale, QSizeF(self.size()) / scale)

    def _camera(self, progress: float) -> tuple[QPointF, float]:
        """How the board is shifted and magnified at this point in the zoom.

        It grows about the card and slides to follow it, but never so far that an edge of
        the board comes into view.
        """
        scale = _mix(1.0, BOARD_ZOOM, progress)
        shift = self._current(progress).center() - self.origin.center() * scale
        width, height = self.width(), self.height()
        shift.setX(min(0.0, max(width - width * scale, shift.x())))
        shift.setY(min(0.0, max(height - height * scale, shift.y())))
        return shift, scale

    def _current(self, progress: float | None = None) -> QRectF:
        """Where the card is drawn at this point in the zoom, or at `progress` through it."""
        target = self._target()
        p = self.progress if progress is None else progress
        return QRectF(
            _mix(self.origin.left(), target.left(), p),
            _mix(self.origin.top(), target.top(), p),
            _mix(self.origin.width(), target.width(), p),
            _mix(self.origin.height(), target.height(), p),
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """The board flying past, dimmed, and the card on its way to or from the middle."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(board_bg()))
        current = self._current()
        # The board rushes past as the card comes closer, and blurs as it goes. The blurred
        # board was taken fully zoomed, so it is carried along with the sharp one, and meets
        # the screen exactly, unstretched, when the zoom is done.
        if not self.backdrop.isNull():
            shift, scale = self._camera(self.progress)
            painter.save()
            painter.translate(shift)
            painter.scale(scale, scale)
            painter.drawPixmap(QPointF(0, 0), self.backdrop)
            painter.restore()
        focus = (self.progress - BLUR_FROM) / (1.0 - BLUR_FROM)
        if not self.blurred.isNull() and focus > 0:
            shift, scale = self._camera(self.progress)
            _, end_scale = self._camera(1.0)
            painter.save()
            painter.setOpacity(focus)
            painter.translate(shift)
            painter.scale(scale, scale)
            painter.translate(self.blur_area.topLeft())
            painter.scale(1 / end_scale, 1 / end_scale)
            painter.drawImage(QPointF(0, 0), self.blurred)
            painter.restore()
        painter.fillRect(self.rect(), QColor(0, 0, 0, int(255 * DIM * self.progress)))
        if self.form is not None and self.form.isVisible():
            return  # the form is there, and draws itself
        path = QPainterPath()
        path.addRoundedRect(current, 10 + 4 * self.progress, 10 + 4 * self.progress)
        painter.fillPath(path, QColor(surface()))
        painter.save()
        painter.setClipPath(path)
        # The face gives way to the open form as it is blown up, before it gets blurry: a
        # card by a little over halfway there, a small button almost at once.
        grown = max(
            current.width() / max(self.origin.width(), 1.0),
            current.height() / max(self.origin.height(), 1.0),
        )
        reveal = min(1.0, max(0.0, (grown - FADE_FROM) / (FADE_TO - FADE_FROM)))
        if not self.face.isNull():
            painter.setOpacity(1.0 - reveal)
            painter.drawPixmap(current, self.face, QRectF(self.face.rect()))
        if not self.sheet.isNull():
            painter.setOpacity(reveal)
            painter.drawPixmap(current, self.sheet, QRectF(self.sheet.rect()))
        painter.restore()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt's name
        """Keep covering the board when it changes size."""
        if watched is self.board and event.type() == event.Type.Resize and self.isVisible():
            self.setGeometry(self.board.rect())
            if self.animation.state() != QVariantAnimation.Running:
                self._place_form()
                self._focus()
        return False

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """A click beside the card closes it, unless that would throw away what was typed."""
        event.accept()
        if self.form is None or not self.form.isVisible():
            return
        if not getattr(self.form, "changed", False):
            self.close_card()

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """The board stays put while a card is open."""
        event.accept()


def _blurred(picture: QImage, radius: int) -> QImage:
    """A Gaussian-blurred copy of a picture, the same size, `radius` in device pixels.

    The picture is laid over a stretched copy of itself before blurring, so its edges blur
    into more of the board rather than fading into nothing.
    """
    ratio = picture.devicePixelRatio()
    sharp = QImage(picture)
    sharp.setDevicePixelRatio(1.0)
    pad = radius * 2
    padded = QPixmap(sharp.width() + 2 * pad, sharp.height() + 2 * pad)
    painter = QPainter(padded)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage(QRectF(padded.rect()), sharp)
    painter.drawImage(QPointF(pad, pad), sharp)
    painter.end()

    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(padded)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius)
    effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    soft = QImage(sharp.size(), QImage.Format_ARGB32_Premultiplied)
    soft.fill(Qt.transparent)
    painter = QPainter(soft)
    source = QRectF(pad, pad, sharp.width(), sharp.height())
    scene.render(painter, QRectF(soft.rect()), source)
    painter.end()
    soft.setDevicePixelRatio(ratio)
    return soft


def _mix(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


def _location_box(locations, current: str) -> QComboBox:
    box = QComboBox()
    box.setEditable(True)
    box.addItem("")
    box.addItems(list(locations))
    box.setCurrentText(current)
    completer = box.completer()
    completer.setCompletionMode(QCompleter.PopupCompletion)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    return box


def _risk_box(current: Risk) -> QComboBox:
    box = QComboBox()
    for risk in Risk:
        box.addItem(f"{risk.value} - {RISK_LABELS[risk.value].split(' - ')[-1]}", risk.value)
    box.setCurrentIndex(list(Risk).index(current))
    box.currentIndexChanged.connect(lambda _: _tint(box))
    _tint(box)
    return box


def _tint(box: QComboBox) -> None:
    box.setStyleSheet(f"font-weight: 600; color: {risk_color(box.currentData())};")


def _flag_grid(flags: dict[str, QCheckBox]) -> QWidget:
    holder = QWidget()
    grid = QGridLayout(holder)
    grid.setContentsMargins(0, 0, 0, 0)
    for index, box in enumerate(flags.values()):
        grid.addWidget(box, index // 2, index % 2)
    return holder
