"""What the window shows before a week is open: sign in, link a folder, or make the week."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from brainwaves.palette import LINE, SURFACE


class WelcomePage(QWidget):
    """One centred panel with one thing to do next."""

    acted = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.panel = QFrame()
        self.panel.setStyleSheet(
            f"QFrame {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 14px; }}"
        )
        self.panel.setFixedWidth(460)
        self.title = QLabel("Brain Waves")
        self.title.setObjectName("wordmark")
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setObjectName("cardDescription")
        self.button = QPushButton()
        self.button.setObjectName("primary")
        self.button.clicked.connect(self.acted)
        self.detail = QLabel()
        self.detail.setObjectName("hint")
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)

        inner = QVBoxLayout(self.panel)
        inner.setContentsMargins(28, 26, 28, 26)
        inner.setSpacing(12)
        inner.addWidget(self.title)
        inner.addWidget(self.message)
        inner.addWidget(self.button)
        inner.addWidget(self.detail)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self.panel, 0, Qt.AlignHCenter)
        layout.addStretch(2)

    def show_step(self, message: str, action: str, detail: str = "") -> None:
        """Say what is needed and what the button will do about it."""
        self.message.setText(message)
        self.button.setText(action)
        self.button.setVisible(bool(action))
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))
