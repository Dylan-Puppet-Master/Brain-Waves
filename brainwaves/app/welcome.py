"""What the window shows before a week is open: sign in, link a folder, or make the week."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from brainwaves.app.activity import sweeping_bar
from brainwaves.app.widgets import height_follows_width

PANEL_WIDTH = 460
PANEL_PADDING = 28
TEXT_WIDTH = PANEL_WIDTH - 2 * PANEL_PADDING


class WelcomePage(QWidget):
    """One centred panel with one thing to do next."""

    acted = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.panel = QFrame()
        self.panel.setObjectName("welcomePanel")
        self.panel.setFixedWidth(PANEL_WIDTH)
        self.title = QLabel("Brain Waves")
        self.title.setObjectName("wordmark")
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setObjectName("welcomeMessage")
        height_follows_width(self.message)
        self.button = QPushButton()
        self.button.setObjectName("primary")
        self.button.clicked.connect(self.acted)
        self.detail = QLabel()
        self.detail.setObjectName("hint")
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        height_follows_width(self.detail)
        self.bar = sweeping_bar(6)
        self.bar.hide()

        inner = QVBoxLayout(self.panel)
        inner.setContentsMargins(PANEL_PADDING, 26, PANEL_PADDING, 26)
        inner.setSpacing(12)
        inner.addWidget(self.title)
        inner.addWidget(self.message)
        inner.addWidget(self.button)
        inner.addWidget(self.bar)
        inner.addWidget(self.detail)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self.panel, 0, Qt.AlignHCenter)
        layout.addStretch(2)

    def show_step(self, message: str, action: str, detail: str = "") -> None:
        """Say what is needed and what the button will do about it."""
        self._say(self.message, message)
        self.button.setText(action)
        self.button.setVisible(bool(action))
        self.bar.hide()
        self._say(self.detail, detail)

    def show_working(self, message: str, detail: str = "") -> None:
        """Say what is being done, with a bar, and offer nothing to press."""
        self._say(self.message, message)
        self.button.hide()
        self.bar.show()
        self._say(self.detail, detail)

    def say(self, detail: str) -> None:
        """Name the step being worked on, while the bar keeps sweeping."""
        self._say(self.detail, detail)

    @staticmethod
    def _say(label: QLabel, text: str) -> None:
        """Set a wrapped label's text and give it the room that text needs.

        The panel is a fixed width, so nothing ever asks the label how tall it wants to be
        and a second line is silently cut off. Asking it here is the whole fix.
        """
        label.setText(text)
        label.setVisible(bool(text))
        label.setMinimumHeight(label.heightForWidth(TEXT_WIDTH) if text else 0)
