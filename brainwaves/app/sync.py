"""Talking to Google without freezing the window.

One thread runs one job at a time, in the order they were asked for, so a card that was
moved and then edited reaches the sheet in that order. Jobs report back through signals,
which Qt delivers on the UI thread.
"""

import queue
import traceback
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

STOP = object()


class JobQueue(QThread):
    """A worker that runs submitted callables in order and reports what happened."""

    done = Signal(str, object)
    failed = Signal(str, str)
    idle = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._jobs: queue.Queue = queue.Queue()

    def submit(self, name: str, work: Callable[[], object]) -> None:
        """Ask for a job to run. `name` comes back with its result."""
        self._jobs.put((name, work))

    def stop(self) -> None:
        """Finish the jobs already asked for, then end the thread."""
        self._jobs.put(STOP)
        self.wait(5000)

    @property
    def waiting(self) -> int:
        """How many jobs have not started."""
        return self._jobs.qsize()

    def run(self) -> None:
        """Run jobs until asked to stop."""
        while True:
            job = self._jobs.get()
            if job is STOP:
                return
            name, work = job
            try:
                result = work()
            except Exception as e:  # noqa: BLE001 - reported to the user, never swallowed
                self.failed.emit(name, _message(e))
            else:
                self.done.emit(name, result)
            if self._jobs.empty():
                self.idle.emit()


def _message(error: Exception) -> str:
    text = str(error).strip()
    return text or traceback.format_exc(limit=3)
