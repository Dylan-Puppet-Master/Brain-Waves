"""The documentation must describe the program that exists."""

import re
from pathlib import Path

import pytest

from brainwaves.cli import main
from brainwaves.sheets import layout
from brainwaves.sheets.week import BOARD_TAB, LOCATIONS_TAB, REQUESTS_TAB, ROSTER_TAB

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
NAV = re.compile(r"^\s+-\s+.+:\s+(\S+\.md)\s*$", re.MULTILINE)


def nav_pages() -> list[str]:
    return NAV.findall((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))


def test_every_page_in_the_nav_exists():
    pages = nav_pages()
    assert pages
    missing = [page for page in pages if not (DOCS / page).exists()]
    assert missing == []


def test_every_page_is_in_the_nav():
    pages = set(nav_pages())
    assert {path.name for path in DOCS.glob("*.md")} == pages


def test_the_screenshot_the_home_page_shows_is_there():
    assert "img/app.png" in (DOCS / "index.md").read_text(encoding="utf-8")
    assert (DOCS / "img" / "app.png").exists()


@pytest.mark.parametrize("tab", [BOARD_TAB, ROSTER_TAB, LOCATIONS_TAB, REQUESTS_TAB])
def test_the_sheets_page_names_every_tab(tab):
    assert tab in (DOCS / "sheets.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("label", layout.FIELD_LABELS)
def test_the_sheets_page_shows_every_card_row(label):
    assert label in (DOCS / "sheets.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("label", [flag for flag in layout.FLAG_LABELS if flag])
def test_the_sheets_page_shows_every_card_flag(label):
    assert label in (DOCS / "sheets.md").read_text(encoding="utf-8")


def test_the_install_page_lists_every_command(capsys):
    text = (DOCS / "install.md").read_text(encoding="utf-8")
    for command in ("sign-in", "sign-out", "where", "template"):
        assert f"brainwaves {command}" in text
    assert main(["where"]) == 0
    printed = capsys.readouterr().out
    assert "config" in printed and "sign-in" in printed
