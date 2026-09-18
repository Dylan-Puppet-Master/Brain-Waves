"""Render the window against a sample week and save it, so the docs picture stays true.

QT_QPA_PLATFORM=offscreen python tools/screenshot.py docs/img/app.png
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("BRAINWAVES_DATA", tempfile.mkdtemp())
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from brainwaves.app.main import MainWindow  # noqa: E402
from brainwaves.app.theme import apply_theme  # noqa: E402
from brainwaves.config import Config  # noqa: E402
from brainwaves.store import BoardStore  # noqa: E402
from tests.fakes import build  # noqa: E402
from tools.sample import SAMPLE_LOCATIONS, SAMPLE_STAFF, sample_week  # noqa: E402


def main(destination: Path) -> None:
    """Draw the sample week and write a PNG."""
    week = sample_week()
    workspace, sheet = build(tempfile.mkdtemp(), week, locations=SAMPLE_LOCATIONS)
    store = BoardStore(workspace, sheet)
    store.staff_names = SAMPLE_STAFF
    store.add_comment("a1", "Do we have a low ropes facilitator free on Monday?")
    store.add_comment("e1", "This needs a van and a director sign-off. Who is driving?")
    store.flush()
    store.reply(store.comments[-1].id, "Dylan is free - I have pencilled him in.")
    store.flush()

    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    window = MainWindow(Config())
    window.resize(1600, 980)
    window.store = store
    window.sheet_label.setText("Cabin Act Sorting - S2W1 - Cabin Acts 2026")
    window._draw()
    window.select_card("a1")
    window._set_busy("")
    window.show()
    for _ in range(8):
        app.processEvents()
    destination.parent.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(destination))
    window.jobs.stop()
    print(f"Saved {destination}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "docs/img/app.png"))
