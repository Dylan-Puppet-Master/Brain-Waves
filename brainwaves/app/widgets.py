"""Small pieces the rest of the window is built from: chips, a flow layout, a time phrase."""

from datetime import UTC, datetime

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLabel, QLayout, QSizePolicy, QWidget

from brainwaves.app.theme import risk_color
from brainwaves.palette import RISK_LABELS


def chip(text: str, name: str = "chip", tooltip: str = "") -> QLabel:
    """A small rounded label. `name` picks its look out of the stylesheet."""
    label = QLabel(text)
    label.setObjectName(name)
    label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    if tooltip:
        label.setToolTip(tooltip)
    return label


def risk_chip(risk_value: str) -> QLabel:
    """The coloured R / Y / G badge."""
    label = chip(risk_value, "riskChip", RISK_LABELS.get(risk_value, risk_value))
    label.setStyleSheet(f"background: {risk_color(risk_value)};")
    return label


def elided(label: QLabel, text: str, width: int, lines: int = 1) -> None:
    """Put `text` on a label, cut to fit `lines` rows of `width` pixels."""
    metrics = label.fontMetrics()
    if lines == 1:
        label.setText(metrics.elidedText(text, Qt.ElideRight, width))
        return
    words, rows, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if metrics.horizontalAdvance(trial) <= width:
            current = trial
            continue
        rows.append(current)
        current = word
        if len(rows) == lines:
            break
    if len(rows) < lines and current:
        rows.append(current)
    joined = "\n".join(rows)
    if len(rows) == lines and len(joined) < len(text):
        rows[-1] = metrics.elidedText(rows[-1] + " " + text[len(joined) :], Qt.ElideRight, width)
        joined = "\n".join(rows)
    label.setText(joined)


AGO = ((3600, 60, "minute"), (86400, 3600, "hour"), (7 * 86400, 86400, "day"))


def when_phrase(moment: datetime) -> str:
    """How long ago something happened, in words, or its date once that stops mattering."""
    seconds = (datetime.now(UTC) - moment.astimezone(UTC)).total_seconds()
    if seconds < 90:
        return "just now"
    for limit, divisor, unit in AGO:
        if seconds < limit:
            count = int(seconds // divisor)
            return f"{count} {unit}{'s' if count != 1 else ''} ago"
    return moment.astimezone().strftime("%d %b")


class FlowLayout(QLayout):
    """Lays widgets out left to right, wrapping onto the next line. Used by the chip bars."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 4) -> None:
        super().__init__(parent)
        self._items: list = []
        self._spacing = spacing
        self.setContentsMargins(QMargins(0, 0, 0, 0))

    def addItem(self, item) -> None:  # noqa: N802 - Qt's name
        """Take ownership of a layout item."""
        self._items.append(item)

    def count(self) -> int:
        """How many items are laid out."""
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802 - Qt's name
        """The item at `index`, or None."""
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # noqa: N802 - Qt's name
        """Remove and return the item at `index`."""
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802 - Qt's name
        """The layout never asks for more room in either direction."""
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt's name
        """Height depends on width, because the items wrap."""
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt's name
        """How tall the items are once wrapped into `width`."""
        return self._lay_out(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802 - Qt's name
        """Place the items."""
        super().setGeometry(rect)
        self._lay_out(rect, apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt's name
        """The size of the widest item, which is the smallest sensible width."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802 - Qt's name
        """Big enough for the largest single item."""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _lay_out(self, rect: QRect, apply: bool) -> int:
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x > rect.x() and x + hint.width() > rect.right():
                x, y = rect.x(), y + line_height + self._spacing
                line_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()
