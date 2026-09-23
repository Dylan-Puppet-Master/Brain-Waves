"""The window's look: one stylesheet, built from the palette the sheet template also uses.

Widgets ask for a look by object name or by a dynamic property, so the rules below are the
only place a colour is chosen. Changing `brainwaves.palette` changes the app and the
Google Sheets template together.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from brainwaves.palette import (
    ACCENT,
    ACCENT_DARK,
    ACCENT_SOFT,
    CLASH,
    FAINT,
    INK,
    LINE,
    MUTED,
    PANEL,
    RISK_COLORS,
    SUNKEN,
    SURFACE,
    VILLAGE_COLORS,
)

CARD_WIDTH = 250
CARD_HEIGHT = 175
SLOT_PADDING = 8
CABIN_WIDTH = 150

WARN_BG = "#fdf0dc"
WARN_INK = "#8a5200"

# The board is laid on a warm off-white, easier on the eye over an afternoon than the cool
# grey of the window around it. The row and column under the cursor are shaded a little
# deeper, so a card can be read across to its cabin and up to its day.
BOARD_BG = "#F5F5F5"
BOARD_CROSS = "#D1D1D1"

STYLESHEET = f"""
QWidget {{
    color: {INK};
    font-size: 13px;
}}
QMainWindow, QDialog {{ background: {SUNKEN}; }}

QToolBar#chrome {{
    background: {SURFACE};
    border-bottom: 1px solid {LINE};
    padding: 6px 10px;
    spacing: 8px;
}}
QLabel#wordmark {{
    color: {ACCENT};
    font-size: 18px;
    font-weight: 700;
    padding-right: 8px;
}}
QLabel#sheetName {{ color: {MUTED}; }}
QLabel#status {{ color: {MUTED}; }}
QLabel#statusBusy {{ color: {ACCENT}; }}
QLabel#statusError {{ color: #b3261e; font-weight: 600; }}

QPushButton {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 5px 12px;
}}
QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton:pressed {{ background: {ACCENT_SOFT}; }}
QPushButton:disabled {{ color: {FAINT}; border-color: {LINE}; }}
QPushButton#primary {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: {SURFACE};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background: {ACCENT_DARK};
    border-color: {ACCENT_DARK};
    color: {SURFACE};
}}
QPushButton#primary:disabled {{
    background: {SUNKEN};
    border-color: {LINE};
    color: {FAINT};
}}
QPushButton#quiet {{ border-color: transparent; background: transparent; color: {MUTED}; }}
QPushButton#quiet:hover {{ color: {ACCENT}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {INK};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 15px; border: none; }}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {LINE};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {INK};
    outline: none;
}}
QCheckBox {{ spacing: 7px; }}

QScrollArea {{ border: none; background: {SUNKEN}; }}
QWidget#boardView, QWidget#boardView QScrollArea {{ background: {BOARD_BG}; }}
QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; margin: 0; }}
QScrollBar:vertical {{ width: 11px; }}
QScrollBar:horizontal {{ height: 11px; }}
QScrollBar::handle {{ background: #c3ccd6; border-radius: 5px; min-height: 36px; min-width: 36px; }}
QScrollBar::handle:hover {{ background: {MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QWidget#dayHeader {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 8px;
}}
QWidget#dayHeader[weekend="true"] {{ background: {PANEL}; }}
QLabel#dayName {{ font-size: 17px; font-weight: 700; }}
QLineEdit#daySubtitle {{
    border: none;
    background: transparent;
    color: {ACCENT};
    padding: 0;
    font-size: 14px;
    font-weight: 600;
}}
QLineEdit#daySubtitle:hover {{ background: {ACCENT_SOFT}; border-radius: 4px; }}
QLabel#unplacedName {{ color: {MUTED}; font-size: 16px; font-weight: 700; }}
QPushButton#addColumn {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 6px;
    color: {MUTED};
    font-weight: 700;
    padding: 0;
}}
QPushButton#addColumn:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton#addChip {{
    background: {ACCENT_SOFT};
    border: 1px dashed {ACCENT};
    border-radius: 9px;
    color: {ACCENT_DARK};
    font-size: 12px;
    font-weight: 700;
    padding: 3px 10px;
}}
QPushButton#addChip:hover {{ background: {SURFACE}; border-style: solid; }}
QFrame#chipPill {{
    background: {ACCENT_SOFT};
    border: 1px solid {ACCENT_SOFT};
    border-radius: 11px;
}}
QFrame#chipPill:hover {{ border-color: {ACCENT}; }}
QFrame#chipPill[kind="category"], QFrame#chipPill[kind="skill"] {{
    background: {SURFACE};
    border: 1px dashed {ACCENT};
}}
QLabel#chipPillName {{
    color: {ACCENT_DARK};
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#chipPillClose {{
    background: transparent;
    border: none;
    color: {ACCENT};
    font-size: 15px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#chipPillClose:hover {{ color: #b3261e; }}

QFrame#cabinTile {{ border-radius: 8px; }}
QLabel#cabinName {{ font-size: 18px; font-weight: 700; }}
QLabel#cabinWho {{ font-size: 17px; font-weight: 600; }}

QFrame#slot {{
    border: 1px dashed transparent;
    border-radius: 12px;
}}
QFrame#slot[hover="true"] {{
    border: 1px dashed {ACCENT};
    background: {ACCENT_SOFT};
}}
QFrame#slot[available="true"] {{
    background: #eef4f3;
    border: 1px dashed #b7d4d0;
}}

QFrame#card {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 10px;
}}
QFrame#card:hover {{ border-color: #b8c3cf; }}
QFrame#card[selected="true"] {{ border: 2px solid {ACCENT}; }}
QFrame#card[lifted="true"] {{ background: {PANEL}; }}
QFrame#card[clash="true"] {{ border: 2px solid {CLASH}; background: #fdf3f2; }}
QLabel#cardTitle {{ font-size: 15px; font-weight: 700; }}
QLabel#cardDescription {{ color: {MUTED}; font-size: 13px; }}
QLabel#cardLocation {{ color: {INK}; font-size: 13px; font-weight: 600; }}
QLabel#cardEmpty {{ color: {FAINT}; font-size: 26px; font-weight: 300; }}
QFrame#addCard {{
    background: transparent;
    border: 1px dashed #c3ccd6;
    border-radius: 10px;
}}
QFrame#addCard:hover {{ border-color: {ACCENT}; background: {ACCENT_SOFT}; }}

QLabel#chip {{
    background: {ACCENT_SOFT};
    color: {ACCENT_DARK};
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#groupChip {{
    background: {SURFACE};
    color: {ACCENT_DARK};
    border: 1px dashed {ACCENT};
    border-radius: 9px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#flagChip {{
    background: {PANEL};
    color: {MUTED};
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#riskChip {{
    border-radius: 9px;
    padding: 3px 10px;
    color: {SURFACE};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#commentBadge {{
    background: {WARN_BG};
    color: {WARN_INK};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 12px;
    font-weight: 700;
}}

QFrame#welcomePanel {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 14px;
}}
QFrame#welcomePanel > QLabel {{ border: none; background: transparent; }}
QLabel#welcomeMessage {{ color: {MUTED}; font-size: 14px; }}

QProgressBar {{
    background: {SUNKEN};
    border: none;
    border-radius: 2px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 2px;
}}

QDockWidget {{ titlebar-close-icon: none; font-weight: 600; }}
QDockWidget::title {{
    background: {SURFACE};
    border-bottom: 1px solid {LINE};
    padding: 8px 10px;
}}
QWidget#panel {{ background: {SURFACE}; border-left: 1px solid {LINE}; }}
QFrame#thread {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 8px;
}}
QFrame#thread[resolved="true"] {{ background: {PANEL}; }}
QLabel#threadAuthor {{ font-weight: 700; font-size: 13px; }}
QLabel#threadWhen {{ color: {FAINT}; font-size: 12px; }}
QLabel#threadText {{ font-size: 13px; }}
QLabel#replyAuthor {{ color: {MUTED}; font-weight: 600; font-size: 12px; }}
QLabel#hint {{ color: {FAINT}; font-size: 12px; }}
QLabel#sectionTitle {{ color: {MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}

QTableWidget {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 6px;
    alternate-background-color: {PANEL};
    gridline-color: transparent;
}}
QTableWidget::item {{ padding: 5px 7px; }}
QTableWidget::item:selected {{ background: {ACCENT_SOFT}; color: {INK}; }}
QHeaderView::section {{
    background: {PANEL};
    border: none;
    border-bottom: 1px solid {LINE};
    color: {MUTED};
    font-size: 11px;
    font-weight: 700;
    padding: 5px 7px;
}}

QListWidget {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px; }}
QListWidget::item {{ padding: 5px 8px; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {INK}; }}
"""


def apply_theme(app: QApplication) -> None:
    """Put the palette and the stylesheet on the application."""
    app.setStyle("Fusion")
    app.setPalette(_palette())
    font = QFont(app.font())
    font.setPointSizeF(max(font.pointSizeF(), 10.0))
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)


def restyle(widget: QWidget) -> None:
    """Make a widget pick up a dynamic property that has just changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def risk_color(risk_value: str) -> str:
    """The colour of a risk level."""
    return RISK_COLORS.get(risk_value, RISK_COLORS["N"])


def village_pair(village: str) -> tuple[str, str]:
    """Line and fill colours for a village."""
    return VILLAGE_COLORS.get(village, (MUTED, PANEL))


def _palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(SUNKEN))
    palette.setColor(QPalette.Base, QColor(SURFACE))
    palette.setColor(QPalette.AlternateBase, QColor(PANEL))
    palette.setColor(QPalette.Text, QColor(INK))
    palette.setColor(QPalette.WindowText, QColor(INK))
    palette.setColor(QPalette.ButtonText, QColor(INK))
    palette.setColor(QPalette.Button, QColor(SURFACE))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor(SURFACE))
    palette.setColor(QPalette.ToolTipBase, QColor(INK))
    palette.setColor(QPalette.ToolTipText, QColor(SURFACE))
    return palette
