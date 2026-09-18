"""The comments panel: every thread about the card that is selected.

Threads are Google Drive's, so what is written here appears in the Google Sheets comment
sidebar, and what is written there appears here.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from brainwaves.app.theme import restyle
from brainwaves.app.widgets import when_phrase
from brainwaves.model import CabinAct, Comment


class CommentPanel(QWidget):
    """Threads about one card, with a box to start another."""

    comment_added = Signal(str, str)
    reply_added = Signal(str, str)
    resolved = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.setMinimumWidth(320)
        self.card: CabinAct | None = None
        self.comments: list[Comment] = []

        self.heading = QLabel("No card selected")
        self.heading.setObjectName("cardTitle")
        self.heading.setWordWrap(True)
        self.where = QLabel("")
        self.where.setObjectName("hint")
        self.show_resolved = QCheckBox("Show resolved")
        self.show_resolved.toggled.connect(self._redraw)

        self.threads = QWidget()
        self.thread_layout = QVBoxLayout(self.threads)
        self.thread_layout.setContentsMargins(0, 0, 0, 0)
        self.thread_layout.setSpacing(8)
        self.thread_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.threads)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.draft = QTextEdit()
        self.draft.setFixedHeight(64)
        self.draft.setPlaceholderText("Start a comment about this card")
        self.post = QPushButton("Comment")
        self.post.setObjectName("primary")
        self.post.clicked.connect(self._post)

        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.post)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        layout.addWidget(self.heading)
        layout.addWidget(self.where)
        layout.addWidget(self.show_resolved)
        layout.addWidget(scroll, 1)
        layout.addWidget(self.draft)
        layout.addLayout(footer)
        self._set_enabled(False)

    def show_card(self, card: CabinAct | None, where: str, comments: list[Comment]) -> None:
        """Point the panel at a card, or at nothing."""
        self.card = card
        self.comments = comments
        self.heading.setText(card.title or "Untitled" if card else "No card selected")
        self.where.setText(where if card else "Click a card to read and write its comments")
        self._set_enabled(card is not None)
        self._redraw()

    def _set_enabled(self, on: bool) -> None:
        self.draft.setEnabled(on)
        self.post.setEnabled(on)

    def _post(self) -> None:
        text = self.draft.toPlainText().strip()
        if not (text and self.card):
            return
        self.draft.clear()
        self.comment_added.emit(self.card.id, text)

    def _redraw(self) -> None:
        while self.thread_layout.count() > 1:
            item = self.thread_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        shown = [c for c in self.comments if self.show_resolved.isChecked() or not c.resolved]
        if self.card is not None and not shown:
            empty = QLabel("No comments yet.")
            empty.setObjectName("hint")
            self.thread_layout.insertWidget(0, empty)
        for index, comment in enumerate(shown):
            self.thread_layout.insertWidget(index, self._thread(comment))

    def _thread(self, comment: Comment) -> QFrame:
        frame = QFrame()
        frame.setObjectName("thread")
        frame.setProperty("resolved", comment.resolved)
        restyle(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        layout.addLayout(_byline(comment.author, comment.created, comment.resolved))
        layout.addWidget(_body(comment.text))
        for reply in comment.replies:
            layout.addLayout(_byline(reply.author, reply.created, False, small=True))
            layout.addWidget(_body(reply.text))
        if not comment.resolved:
            layout.addLayout(self._reply_row(comment))
        return frame

    def _reply_row(self, comment: Comment) -> QHBoxLayout:
        field = QLineEdit()
        field.setPlaceholderText("Reply")
        field.returnPressed.connect(lambda: self._send_reply(comment.id, field))
        resolve = QPushButton("Resolve")
        resolve.setObjectName("quiet")
        resolve.clicked.connect(lambda: self.resolved.emit(comment.id))
        row = QHBoxLayout()
        row.addWidget(field, 1)
        row.addWidget(resolve)
        return row

    def _send_reply(self, comment_id: str, field: QLineEdit) -> None:
        text = field.text().strip()
        if not text:
            return
        field.clear()
        self.reply_added.emit(comment_id, text)


def _byline(author: str, created, resolved: bool, small: bool = False) -> QHBoxLayout:
    name = QLabel(author)
    name.setObjectName("replyAuthor" if small else "threadAuthor")
    when = QLabel(when_phrase(created) + (" - resolved" if resolved else ""))
    when.setObjectName("threadWhen")
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addWidget(name)
    row.addWidget(when)
    row.addStretch(1)
    return row


def _body(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("threadText")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label
