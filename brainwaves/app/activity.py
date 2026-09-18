"""Saying that something is happening.

Two indicators, because there are two kinds of waiting. Saving a card takes a moment and
the board is still worth looking at, so a thin bar sweeps under the toolbar. Opening or
creating a week takes long enough that there is nothing else to do, so the panel says
which step it is on.

Polls say nothing at all. They happen every couple of seconds, and an indicator that
blinks constantly stops meaning anything.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressBar

BAR_HEIGHT = 3


def sweeping_bar(height: int = BAR_HEIGHT) -> QProgressBar:
    """An indeterminate bar. There is no percentage to report, so it just sweeps."""
    bar = QProgressBar()
    bar.setRange(0, 0)
    bar.setTextVisible(False)
    bar.setFixedHeight(height)
    bar.setAlignment(Qt.AlignCenter)
    return bar
