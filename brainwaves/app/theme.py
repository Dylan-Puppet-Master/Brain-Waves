"""The window's look: one stylesheet, built from the palette the sheet template also uses.

Widgets ask for a look by object name or by a dynamic property, so the rules below are the
only place a colour is chosen. Changing `brainwaves.palette` changes the app and the
Google Sheets template together — the Sheets template has no dark mode, so it always keeps
the light values from there. The desktop window instead picks between the light and dark
colour sets below, matching whatever the operating system is set to, and follows it live if
the system theme changes while the window is open.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette
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

# The board is laid on a warm off-white in light mode, easier on the eye over an afternoon
# than the cool grey of the window around it, and on a matching dark slate in dark mode. The
# row and column under the cursor are shaded a little deeper, so a card can be read across
# to its cabin and up to its day.
_LIGHT = {
    "INK": INK,
    "MUTED": MUTED,
    "FAINT": FAINT,
    "SURFACE": SURFACE,
    "PANEL": PANEL,
    "SUNKEN": SUNKEN,
    "LINE": LINE,
    "ACCENT": ACCENT,
    "ACCENT_SOFT": ACCENT_SOFT,
    "ACCENT_DARK": ACCENT_DARK,
    "BOARD_BG": "#F5F5F5",
    "BOARD_CROSS": "#D1D1D1",
    "WARN_BG": "#fdf0dc",
    "WARN_INK": "#8a5200",
    "CLASH": CLASH,
    "CLASH_BG": "#fdf3f2",
    "DANGER": "#b3261e",
    "SUBTLE_LINE": "#c3ccd6",
    "CARD_HOVER_LINE": "#b8c3cf",
    "CHIP_TEXT": "#ffffff",
}

_DARK = {
    "INK": "#e5e9ee",
    "MUTED": "#9aa7b4",
    "FAINT": "#6b7583",
    "SURFACE": "#1e252d",
    "PANEL": "#262e37",
    "SUNKEN": "#14191f",
    "LINE": "#333d48",
    "ACCENT": "#2dd4bf",
    "ACCENT_SOFT": "#153834",
    "ACCENT_DARK": "#5eead4",
    "BOARD_BG": "#181e25",
    "BOARD_CROSS": "#2a333d",
    "WARN_BG": "#3a2d14",
    "WARN_INK": "#e8b34d",
    "CLASH": "#ff6b6b",
    "CLASH_BG": "#3a2220",
    "DANGER": "#ff6b6b",
    "SUBTLE_LINE": "#3a4452",
    "CARD_HOVER_LINE": "#46505c",
    "CHIP_TEXT": "#ffffff",
}

_VILLAGE_DARK = {
    "Pine": ("#6fcf87", "#17301f"),
    "Cedar": ("#d9a066", "#332415"),
    "Manzi": ("#e88fb9", "#33202a"),
    "Oak": ("#a897e0", "#241f38"),
}


def _dark_mode() -> bool:
    """Whether the operating system is currently set to a dark appearance."""
    hints = QGuiApplication.styleHints()
    return hints.colorScheme() == Qt.ColorScheme.Dark


def _colors() -> dict[str, str]:
    return _DARK if _dark_mode() else _LIGHT


def _stylesheet(c: dict[str, str]) -> str:
    return f"""
QWidget {{
    color: {c["INK"]};
    font-size: 13px;
}}
QMainWindow, QDialog {{ background: {c["SUNKEN"]}; }}

QToolBar#chrome {{
    background: {c["SURFACE"]};
    border-bottom: 1px solid {c["LINE"]};
    padding: 6px 10px;
    spacing: 8px;
}}
QLabel#wordmark {{
    color: {c["ACCENT"]};
    font-size: 18px;
    font-weight: 700;
    padding-right: 8px;
}}
QLabel#sheetName {{ color: {c["MUTED"]}; }}
QLabel#status {{ color: {c["MUTED"]}; }}
QLabel#statusBusy {{ color: {c["ACCENT"]}; }}
QLabel#statusError {{ color: {c["DANGER"]}; font-weight: 600; }}

QPushButton {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 6px;
    padding: 5px 12px;
}}
QPushButton:hover {{ border-color: {c["ACCENT"]}; color: {c["ACCENT"]}; }}
QPushButton:pressed {{ background: {c["ACCENT_SOFT"]}; }}
QPushButton:disabled {{ color: {c["FAINT"]}; border-color: {c["LINE"]}; }}
QPushButton#primary {{
    background: {c["ACCENT"]};
    border-color: {c["ACCENT"]};
    color: {c["CHIP_TEXT"]};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background: {c["ACCENT_DARK"]};
    border-color: {c["ACCENT_DARK"]};
    color: {c["CHIP_TEXT"]};
}}
QPushButton#primary:disabled {{
    background: {c["SUNKEN"]};
    border-color: {c["LINE"]};
    color: {c["FAINT"]};
}}
QPushButton#quiet {{ border-color: transparent; background: transparent; color: {c["MUTED"]}; }}
QPushButton#quiet:hover {{ color: {c["ACCENT"]}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {c["ACCENT_SOFT"]};
    selection-color: {c["INK"]};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {c["ACCENT"]};
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 15px; border: none; }}
QComboBox QAbstractItemView {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    selection-background-color: {c["ACCENT_SOFT"]};
    selection-color: {c["INK"]};
    outline: none;
}}
QCheckBox {{ spacing: 7px; }}

QScrollArea {{ border: none; background: {c["SUNKEN"]}; }}
QWidget#boardView, QWidget#boardView QScrollArea {{ background: {c["BOARD_BG"]}; }}
QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; margin: 0; }}
QScrollBar:vertical {{ width: 11px; }}
QScrollBar:horizontal {{ height: 11px; }}
QScrollBar::handle {{
    background: {c["SUBTLE_LINE"]};
    border-radius: 5px;
    min-height: 36px;
    min-width: 36px;
}}
QScrollBar::handle:hover {{ background: {c["MUTED"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QWidget#dayHeader {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 8px;
}}
QWidget#dayHeader[weekend="true"] {{ background: {c["PANEL"]}; }}
QLabel#dayName {{ font-size: 17px; font-weight: 700; }}
QLineEdit#daySubtitle {{
    border: none;
    background: transparent;
    color: {c["ACCENT"]};
    padding: 0;
    font-size: 14px;
    font-weight: 600;
}}
QLineEdit#daySubtitle:hover {{ background: {c["ACCENT_SOFT"]}; border-radius: 4px; }}
QLabel#unplacedName {{ color: {c["MUTED"]}; font-size: 16px; font-weight: 700; }}
QPushButton#addColumn {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 6px;
    color: {c["MUTED"]};
    font-weight: 700;
    padding: 0;
}}
QPushButton#addColumn:hover {{ border-color: {c["ACCENT"]}; color: {c["ACCENT"]}; }}
QPushButton#addChip {{
    background: {c["ACCENT_SOFT"]};
    border: 1px dashed {c["ACCENT"]};
    border-radius: 9px;
    color: {c["ACCENT_DARK"]};
    font-size: 12px;
    font-weight: 700;
    padding: 3px 10px;
}}
QPushButton#addChip:hover {{ background: {c["SURFACE"]}; border-style: solid; }}
QFrame#chipPill {{
    background: {c["ACCENT_SOFT"]};
    border: 1px solid {c["ACCENT_SOFT"]};
    border-radius: 11px;
}}
QFrame#chipPill:hover {{ border-color: {c["ACCENT"]}; }}
QFrame#chipPill[kind="category"], QFrame#chipPill[kind="skill"] {{
    background: {c["SURFACE"]};
    border: 1px dashed {c["ACCENT"]};
}}
QLabel#chipPillName {{
    color: {c["ACCENT_DARK"]};
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#chipPillClose {{
    background: transparent;
    border: none;
    color: {c["ACCENT"]};
    font-size: 15px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#chipPillClose:hover {{ color: {c["DANGER"]}; }}

QFrame#cabinTile {{ border-radius: 8px; }}
QLabel#cabinName {{ font-size: 18px; font-weight: 700; }}
QLabel#cabinWho {{ font-size: 17px; font-weight: 600; }}

QFrame#slot {{
    border: 1px dashed transparent;
    border-radius: 12px;
}}
QFrame#slot[hover="true"] {{
    border: 1px dashed {c["ACCENT"]};
    background: {c["ACCENT_SOFT"]};
}}

QFrame#card {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 10px;
}}
QFrame#card:hover {{ border-color: {c["CARD_HOVER_LINE"]}; }}
QFrame#card[selected="true"] {{ border: 2px solid {c["ACCENT"]}; }}
QFrame#card[lifted="true"] {{ background: {c["PANEL"]}; }}
QFrame#card[clash="true"] {{ border: 2px solid {c["CLASH"]}; background: {c["CLASH_BG"]}; }}
QLabel#cardTitle {{ font-size: 15px; font-weight: 700; }}
QLabel#cardDescription {{ color: {c["MUTED"]}; font-size: 13px; }}
QLabel#cardLocation {{ color: {c["INK"]}; font-size: 13px; font-weight: 600; }}
QLabel#cardEmpty {{ color: {c["FAINT"]}; font-size: 26px; font-weight: 300; }}
QFrame#cardEditor {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 14px;
}}
QLineEdit#editorTitle {{
    font-size: 22px;
    font-weight: 700;
    border: 1px solid transparent;
    background: transparent;
    padding: 4px 6px;
}}
QLineEdit#editorTitle:hover {{ border-color: {c["LINE"]}; }}
QLineEdit#editorTitle:focus {{ border-color: {c["ACCENT"]}; background: {c["SURFACE"]}; }}
QPushButton#danger {{ color: {c["DANGER"]}; }}
QFrame#addCard {{
    background: transparent;
    border: 1px dashed {c["SUBTLE_LINE"]};
    border-radius: 10px;
}}
QFrame#addCard:hover {{ border-color: {c["ACCENT"]}; background: {c["ACCENT_SOFT"]}; }}

QLabel#chip {{
    background: {c["ACCENT_SOFT"]};
    color: {c["ACCENT_DARK"]};
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#groupChip {{
    background: {c["SURFACE"]};
    color: {c["ACCENT_DARK"]};
    border: 1px dashed {c["ACCENT"]};
    border-radius: 9px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#flagChip {{
    background: {c["PANEL"]};
    color: {c["MUTED"]};
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#riskChip {{
    border-radius: 9px;
    padding: 3px 10px;
    color: {c["CHIP_TEXT"]};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#commentBadge {{
    background: {c["WARN_BG"]};
    color: {c["WARN_INK"]};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 12px;
    font-weight: 700;
}}

QFrame#welcomePanel {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 14px;
}}
QFrame#welcomePanel > QLabel {{ border: none; background: transparent; }}
QLabel#welcomeMessage {{ color: {c["MUTED"]}; font-size: 14px; }}

QProgressBar {{
    background: {c["SUNKEN"]};
    border: none;
    border-radius: 2px;
}}
QProgressBar::chunk {{
    background: {c["ACCENT"]};
    border-radius: 2px;
}}

QDockWidget {{ titlebar-close-icon: none; font-weight: 600; }}
QDockWidget::title {{
    background: {c["SURFACE"]};
    border-bottom: 1px solid {c["LINE"]};
    padding: 8px 10px;
}}
QWidget#panel {{ background: {c["SURFACE"]}; border-left: 1px solid {c["LINE"]}; }}
QFrame#thread {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 8px;
}}
QFrame#thread[resolved="true"] {{ background: {c["PANEL"]}; }}
QLabel#threadAuthor {{ font-weight: 700; font-size: 13px; }}
QLabel#threadWhen {{ color: {c["FAINT"]}; font-size: 12px; }}
QLabel#threadText {{ font-size: 13px; }}
QLabel#replyAuthor {{ color: {c["MUTED"]}; font-weight: 600; font-size: 12px; }}
QLabel#hint {{ color: {c["FAINT"]}; font-size: 12px; }}
QLabel#sectionTitle {{
    color: {c["MUTED"]};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QTableWidget {{
    background: {c["SURFACE"]};
    border: 1px solid {c["LINE"]};
    border-radius: 6px;
    alternate-background-color: {c["PANEL"]};
    gridline-color: transparent;
}}
QTableWidget::item {{ padding: 5px 7px; }}
QTableWidget::item:selected {{ background: {c["ACCENT_SOFT"]}; color: {c["INK"]}; }}
QHeaderView::section {{
    background: {c["PANEL"]};
    border: none;
    border-bottom: 1px solid {c["LINE"]};
    color: {c["MUTED"]};
    font-size: 11px;
    font-weight: 700;
    padding: 5px 7px;
}}

QListWidget {{ background: {c["SURFACE"]}; border: 1px solid {c["LINE"]}; border-radius: 6px; }}
QListWidget::item {{ padding: 5px 8px; }}
QListWidget::item:selected {{ background: {c["ACCENT_SOFT"]}; color: {c["INK"]}; }}
"""


def apply_theme(app: QApplication) -> None:
    """Put the palette and the stylesheet on the application.

    Matches the system's light or dark appearance, and keeps matching it if that appearance
    changes while the app is open.
    """
    app.setStyle("Fusion")
    font = QFont(app.font())
    font.setPointSizeF(max(font.pointSizeF(), 10.0))
    app.setFont(font)
    _restyle_app(app)
    app.styleHints().colorSchemeChanged.connect(lambda _scheme: _restyle_app(app))


def current_stylesheet() -> str:
    """The stylesheet for whichever appearance is active right now."""
    return _stylesheet(_colors())


def _restyle_app(app: QApplication) -> None:
    c = _colors()
    app.setPalette(_palette(c))
    app.setStyleSheet(_stylesheet(c))
    # Widgets that paint themselves (the board) or set an inline colour once at construction
    # time don't pick up a new stylesheet on their own; asking every widget to repaint lets
    # the ones that read the live colours each frame (see `board_bg`, `board_cross`) catch up.
    for widget in app.allWidgets():
        widget.update()


def restyle(widget: QWidget) -> None:
    """Make a widget pick up a dynamic property that has just changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def board_bg() -> str:
    """The board's background colour, light or dark to match the window around it."""
    return _colors()["BOARD_BG"]


def board_cross() -> str:
    """The shade laid behind the row and column under the cursor."""
    return _colors()["BOARD_CROSS"]


def surface() -> str:
    """The colour of a card, light or dark to match the window around it."""
    return _colors()["SURFACE"]


def risk_color(risk_value: str) -> str:
    """The colour of a risk level. The same hue is used in both appearances."""
    return RISK_COLORS.get(risk_value, RISK_COLORS["N"])


def clash_color() -> str:
    """The colour used to flag a clash, light or dark to stay readable on the window."""
    return _colors()["CLASH"]


def village_pair(village: str) -> tuple[str, str]:
    """Line and fill colours for a village."""
    table = _VILLAGE_DARK if _dark_mode() else VILLAGE_COLORS
    return table.get(village, (_colors()["MUTED"], _colors()["PANEL"]))


def _palette(c: dict[str, str]) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["SUNKEN"]))
    palette.setColor(QPalette.Base, QColor(c["SURFACE"]))
    palette.setColor(QPalette.AlternateBase, QColor(c["PANEL"]))
    palette.setColor(QPalette.Text, QColor(c["INK"]))
    palette.setColor(QPalette.WindowText, QColor(c["INK"]))
    palette.setColor(QPalette.ButtonText, QColor(c["INK"]))
    palette.setColor(QPalette.Button, QColor(c["SURFACE"]))
    palette.setColor(QPalette.Highlight, QColor(c["ACCENT"]))
    palette.setColor(QPalette.HighlightedText, QColor(c["CHIP_TEXT"]))
    palette.setColor(QPalette.ToolTipBase, QColor(c["INK"]))
    palette.setColor(QPalette.ToolTipText, QColor(c["SURFACE"]))
    return palette
