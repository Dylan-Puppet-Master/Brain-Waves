"""The small windows: pick a Drive folder, start a week, edit the roster."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from brainwaves.google.drive import ROOT
from brainwaves.model import Cabin, sort_cabins
from brainwaves.sheets.week import ROSTER_HEADER

MY_DRIVE = "My Drive"


class FolderDialog(QDialog):
    """Walk down Google Drive and choose the folder the week sheets live in."""

    def __init__(self, drive, parent=None) -> None:
        super().__init__(parent)
        self.drive = drive
        self.setWindowTitle("Link to Google Sheets")
        self.setMinimumSize(460, 420)
        self.trail: list[tuple[str, str]] = [(ROOT, MY_DRIVE)]

        self.breadcrumb = QLabel()
        self.breadcrumb.setObjectName("hint")
        self.breadcrumb.setWordWrap(True)
        self.listing = QListWidget()
        self.listing.itemDoubleClicked.connect(self._descend)
        self.up = QPushButton("Up one folder")
        self.up.clicked.connect(self._ascend)
        self.open_button = QPushButton("Open folder")
        self.open_button.clicked.connect(lambda: self._descend(self.listing.currentItem()))

        buttons = QDialogButtonBox()
        use = buttons.addButton("Use this folder", QDialogButtonBox.AcceptRole)
        use.setObjectName("primary")
        buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        controls = QHBoxLayout()
        controls.addWidget(self.up)
        controls.addWidget(self.open_button)
        controls.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose the folder that holds the Cabin Act Sorting sheets."))
        layout.addWidget(self.breadcrumb)
        layout.addWidget(self.listing, 1)
        layout.addLayout(controls)
        layout.addWidget(buttons)
        self._refresh()

    @property
    def folder(self) -> tuple[str, str]:
        """The chosen folder's id and name."""
        return self.trail[-1]

    def _refresh(self) -> None:
        self.breadcrumb.setText(" / ".join(name for _, name in self.trail))
        self.up.setEnabled(len(self.trail) > 1)
        self.listing.clear()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            folders = self.drive.folders(self.folder[0])
        except Exception as e:  # noqa: BLE001 - shown, never swallowed
            QMessageBox.critical(self, "Could not read Drive", str(e))
            folders = []
        finally:
            QApplication.restoreOverrideCursor()
        for item in folders:
            entry = QListWidgetItem(item.name)
            entry.setData(Qt.UserRole, item.id)
            self.listing.addItem(entry)
        if not folders:
            self.listing.addItem(QListWidgetItem("(no sub-folders here)"))

    def _descend(self, item) -> None:
        if item is None or item.data(Qt.UserRole) is None:
            return
        self.trail.append((item.data(Qt.UserRole), item.text()))
        self._refresh()

    def _ascend(self) -> None:
        if len(self.trail) > 1:
            self.trail.pop()
            self._refresh()


class RosterDialog(QDialog):
    """Add, remove and rename the cabins of a week."""

    def __init__(self, cabins, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cabins")
        self.setMinimumSize(460, 420)
        self.table = QTableWidget(len(cabins), 3)
        self.table.setHorizontalHeaderLabels(ROSTER_HEADER)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        for row, cabin in enumerate(cabins):
            for column, value in enumerate((cabin.name, cabin.counselor, cabin.co_counselor)):
                self.table.setItem(row, column, QTableWidgetItem(value))

        add = QPushButton("Add cabin")
        add.clicked.connect(lambda: self.table.insertRow(self.table.rowCount()))
        remove = QPushButton("Remove selected")
        remove.clicked.connect(self._remove)
        buttons = QDialogButtonBox()
        save = buttons.addButton("Save", QDialogButtonBox.AcceptRole)
        save.setObjectName("primary")
        buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        controls = QHBoxLayout()
        controls.addWidget(add)
        controls.addWidget(remove)
        controls.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Cabin names starting M, P, O or C fall into their village."))
        layout.addWidget(self.table, 1)
        layout.addLayout(controls)
        layout.addWidget(buttons)

    @property
    def cabins(self) -> tuple[Cabin, ...]:
        """The roster as edited, in village order."""
        rows = []
        for row in range(self.table.rowCount()):
            fields = [_text(self.table.item(row, column)) for column in range(3)]
            if fields[0]:
                rows.append(Cabin(*fields))
        return sort_cabins(rows)

    def _remove(self) -> None:
        for index in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(index)


def _text(item) -> str:
    return item.text().strip() if item is not None else ""
