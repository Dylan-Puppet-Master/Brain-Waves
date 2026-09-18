"""The card editor: the same fields the sheet holds, laid out as the card they make."""

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from brainwaves.app.chips import ChipEditor
from brainwaves.app.theme import risk_color
from brainwaves.model import CabinAct, Risk
from brainwaves.names import join_list, split_list
from brainwaves.palette import RISK_LABELS

FLAGS = (
    ("van", "Van needed"),
    ("armory", "Armory"),
    ("picnic", "Picnic"),
    ("food", "Food (not a picnic)"),
)


class CardDialog(QDialog):
    """Edit one cabin act. Accepting returns the card through `result_card`."""

    def __init__(self, card: CabinAct, where: str, locations, staff, parent=None) -> None:
        super().__init__(parent)
        self.card = card
        self.setWindowTitle(f"Cabin act - {where}")
        self.setMinimumWidth(560)

        self.title = QLineEdit(card.title)
        self.title.setPlaceholderText("what the cabin is doing")
        self.description = QTextEdit(card.description)
        self.description.setFixedHeight(72)
        self.materials = QLineEdit(join_list(card.materials))
        self.materials.setPlaceholderText("comma separated")
        self.location = _location_box(locations, card.location)
        self.notes = QTextEdit(card.notes)
        self.notes.setFixedHeight(60)
        self.risk = _risk_box(card.risk)
        self.flags = {field: QCheckBox(label) for field, label in FLAGS}
        for field, box in self.flags.items():
            box.setChecked(getattr(card, field))
        self.heroes = ChipEditor(staff)
        self.heroes.set_values(card.heroes)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)
        form.addRow("Title", self.title)
        form.addRow("Description", self.description)
        form.addRow("Materials", self.materials)
        form.addRow("Location", self.location)
        form.addRow("Notes", self.notes)
        form.addRow("Risk", self.risk)
        form.addRow("Needs", _flag_grid(self.flags))
        form.addRow("HEROES", self.heroes)

        buttons = QDialogButtonBox()
        save = buttons.addButton("Save", QDialogButtonBox.AcceptRole)
        save.setObjectName("primary")
        buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.delete_button = buttons.addButton("Delete", QDialogButtonBox.DestructiveRole)
        self.deleted = False
        self.delete_button.clicked.connect(self._delete)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.title.setFocus()

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

    def _delete(self) -> None:
        self.deleted = True
        self.accept()


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
