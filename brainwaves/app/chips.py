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

from brainwaves.app.widgets import FlowLayout, height_follows_width
from brainwaves.sheets.staff import CATEGORY, PERSON, StaffLists


def describe(name: str, staff: StaffLists) -> str:
    """What a chip means, for a tooltip: a person, or any one of a group."""
    kind = staff.kind_of(name)
    if kind == PERSON:
        return f"{name}, by name"
    how_many = staff.how_many(name)
    group = "in that category" if kind == CATEGORY else "checked off on it"
    return f"Any one of the {how_many} {group}"


class ChipEditor(QWidget):
    """Names as chips, with an add button that completes against the staff list."""

    changed = Signal()

    def __init__(self, staff=None, placeholder: str = "add a HERO") -> None:
        super().__init__()
        self.staff = staff or StaffLists()
        self.options = self.staff.options
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
            completer = QCompleter(list(self.options), self.entry)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            completer.activated.connect(lambda _: self.entry.returnPressed.emit())
            self.entry.setCompleter(completer)
        self.add_button = QPushButton(f"+ {placeholder.split()[-1].upper()}")
        self.add_button.setObjectName("addChip")
        self.add_button.setToolTip(placeholder)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self._start_entry)
        height_follows_width(self)
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
        """Rebuild the chips, keeping the entry and the button as the last two items.

        They are taken out of the layout rather than reparented: `setParent(None)` marks a
        widget hidden, and re-adding it does not bring it back, which is how the add button
        came to be invisible.
        """
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget not in (self.entry, self.add_button):
                widget.deleteLater()
        for name in self.values:
            self._layout.addWidget(_removable(name, self.staff, self._remove))
        self._layout.addWidget(self.entry)
        self._layout.addWidget(self.add_button)
        self.entry.setVisible(False)
        self.add_button.setVisible(True)
        self.updateGeometry()


def _removable(name: str, staff, remove) -> QFrame:
    """One chip, as a pill with a cross that takes it off again."""
    pill = QFrame()
    pill.setObjectName("chipPill")
    pill.setProperty("kind", staff.kind_of(name))
    pill.setToolTip(describe(name, staff))
    layout = QHBoxLayout(pill)
    layout.setContentsMargins(10, 3, 5, 3)
    layout.setSpacing(4)
    label = QLabel(name)
    label.setObjectName("chipPillName")
    close = QPushButton("\u00d7")
    close.setObjectName("chipPillClose")
    close.setFixedSize(18, 18)
    close.setCursor(Qt.PointingHandCursor)
    close.setToolTip(f"Remove {name}")
    close.clicked.connect(lambda: remove(name))
    layout.addWidget(label)
    layout.addWidget(close)
    return pill
