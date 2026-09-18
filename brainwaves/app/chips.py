"""The HERO chips: a row of names taken from the Skills doc, added and removed one at a time."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from brainwaves.app.widgets import FlowLayout
from brainwaves.palette import ACCENT_SOFT


class ChipEditor(QWidget):
    """Names as chips, with an add button that completes against the staff list."""

    changed = Signal()

    def __init__(self, options=(), placeholder: str = "add a HERO") -> None:
        super().__init__()
        self.options = tuple(options)
        self.values: list[str] = []
        self.placeholder = placeholder
        self._layout = FlowLayout(self, spacing=5)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(placeholder)
        self.entry.setFixedWidth(150)
        self.entry.hide()
        self.entry.returnPressed.connect(self._commit)
        self.entry.editingFinished.connect(self._commit)
        if self.options:
            completer = QCompleter(self.options, self.entry)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            completer.activated.connect(lambda _: self.entry.returnPressed.emit())
            self.entry.setCompleter(completer)
        self.add_button = QPushButton("+")
        self.add_button.setObjectName("quiet")
        self.add_button.setFixedWidth(26)
        self.add_button.setToolTip(placeholder)
        self.add_button.clicked.connect(self._start_entry)
        self._redraw()

    def set_values(self, values) -> None:
        """Replace every chip."""
        self.values = [value for value in values if value]
        self._redraw()

    def _start_entry(self) -> None:
        self.entry.clear()
        self.entry.show()
        self.entry.setFocus()

    def _commit(self) -> None:
        name = self.entry.text().strip()
        self.entry.hide()
        if not name or name in self.values:
            return
        self.values.append(name)
        self._redraw()
        self.changed.emit()

    def _remove(self, name: str) -> None:
        self.values = [value for value in self.values if value != name]
        self._redraw()
        self.changed.emit()

    def _redraw(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget in (self.entry, self.add_button):
                widget.setParent(None)
            elif widget is not None:
                widget.deleteLater()
        for name in self.values:
            self._layout.addWidget(_removable(name, self._remove))
        self._layout.addWidget(self.entry)
        self._layout.addWidget(self.add_button)
        self.entry.setVisible(False)
        self.updateGeometry()


def _removable(name: str, remove) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet(f"background: {ACCENT_SOFT}; border-radius: 9px;")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(8, 2, 4, 2)
    layout.setSpacing(2)
    label = QLabel(name)
    label.setObjectName("chip")
    label.setStyleSheet("background: transparent; padding: 0;")
    close = QPushButton("×")
    close.setObjectName("quiet")
    close.setFixedSize(16, 16)
    close.setCursor(Qt.PointingHandCursor)
    close.setToolTip(f"Remove {name}")
    close.clicked.connect(lambda: remove(name))
    layout.addWidget(label)
    layout.addWidget(close)
    return frame
