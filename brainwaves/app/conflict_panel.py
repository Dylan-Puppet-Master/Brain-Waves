"""The clashes pane: everything two cabins have both asked for on the same day.

One row per clash. Choosing a row makes the cards it is about blink on the board, which is
the quickest way to see whether it matters: two cabins at the lake may be fine, two cabins
wanting the same lifeguard is not.
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brainwaves.app.theme import clash_color
from brainwaves.conflicts import HERO

COLUMNS = ("Day", "Clash", "Cabins")
NOTHING = "Nothing clashes. Every cabin has its own place and its own HEROES."


class ConflictPanel(QWidget):
    """A table of clashes. Emits the cards to blink when a row is chosen."""

    picked = Signal(tuple)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.conflicts: list = []

        self.summary = QLabel(NOTHING)
        self.summary.setObjectName("hint")
        self.summary.setWordWrap(True)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._chose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)
        layout.addWidget(self.summary)
        layout.addWidget(self.table, 1)

    def show_conflicts(self, conflicts) -> None:
        """Redraw the table, keeping the chosen row chosen if it is still a clash."""
        chosen = self._chosen_key()
        self.conflicts = list(conflicts)
        self.summary.setText(NOTHING if not conflicts else _counted(conflicts))
        self.table.setVisible(bool(conflicts))
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.conflicts))
        for row, conflict in enumerate(self.conflicts):
            for column, text in enumerate(
                (conflict.when, f"{conflict.kind}: {conflict.what}", ", ".join(conflict.cabins))
            ):
                item = QTableWidgetItem(text)
                item.setToolTip(conflict.summary)
                if column == 1 and conflict.kind == HERO:
                    item.setForeground(QColor(clash_color()))
                self.table.setItem(row, column, item)
        self.table.blockSignals(False)
        self._choose(chosen)

    def _chosen_key(self) -> tuple | None:
        rows = {index.row() for index in self.table.selectedIndexes()}
        if not rows or not self.conflicts:
            return None
        conflict = self.conflicts[min(rows)]
        return _key(conflict)

    def _choose(self, key: tuple | None) -> None:
        if key is None:
            self.picked.emit(())
            return
        for row, conflict in enumerate(self.conflicts):
            if _key(conflict) == key:
                self.table.selectRow(row)
                return
        self.picked.emit(())  # the clash was settled while it was being looked at

    def _chose(self) -> None:
        rows = {index.row() for index in self.table.selectedIndexes()}
        if not rows:
            self.picked.emit(())
            return
        self.picked.emit(self.conflicts[min(rows)].cards)


def _key(conflict) -> tuple:
    return (conflict.kind, conflict.what, conflict.column, conflict.rest_hour)


def _counted(conflicts) -> str:
    kinds = [c.kind for c in conflicts]
    parts = []
    for kind, word in ((HERO, "HERO"), ("Location", "place")):
        count = kinds.count(kind)
        if count:
            parts.append(f"{count} {word}{'s' if count != 1 else ''}")
    return "Wanted twice on one day: " + " and ".join(parts) + ". Choose a row to see where."
