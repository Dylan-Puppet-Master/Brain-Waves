# Development

## Layout

```
brainwaves/
  model.py, names.py, palette.py     domain objects, identifiers, the shared colours
  config.py, built_in.py, defaults.py  settings and saved state, what a release is built with,
                                     what a new week starts with
  sheets/                            layout, parse and render, formatting, Support Requests, staff names
  google/                            auth, Drive, Drive comments, retrying a wobble
  comments.py, conflicts.py          matching Drive threads to cards, finding clashes
  workspace.py                       find, open and create week sheets
  store.py                           one loaded week and every change to it
  app/                               the PySide6 window
  update.py, cli.py                  updating, the brainwaves command
tests/                               pytest, entirely offline; fakes.py stands in for Google
tools/                               the sample week and the screenshot the docs use
docs/                                this site
```

Reading a week is `workspace.Workspace.read` → `sheets.week.parse_week`; writing one is
`sheets.week.card_block` → `sheets.source.SheetsWorkbook.write`. Each stage takes and
returns the dataclasses in `model.py`; nothing holds global state except `BoardStore`,
which holds the one week that is open and the one lock that keeps its two threads apart.

A poll, opening a week and pressing Refresh all call `Workspace.read`, which fetches the
Board, Roster, Locations and Support Requests tabs in one request. Writes are gathered by
`BoardStore._write_dirty` and go out through `SheetsWorkbook.write_batch`, one request for
every card changed since the last write plus the Support Requests tab, when it has changed.

`SheetsWorkbook` talks to gspread's `HTTPClient` rather than its `Spreadsheet`, whose tab
lookups each fetch the whole spreadsheet's metadata again. `tests/test_sheets_workbook.py`
counts the calls it makes; a change that adds one should have a reason.

## Running the tests

```
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

The suite never reaches the network. `tests/fakes.py` stands in for Google: a folder of CSV
files for the spreadsheet and a list for the comments, which is enough to exercise the store
and the whole sheet format. The window tests run headless; `tests/conftest.py` sets
`QT_QPA_PLATFORM=offscreen`.

## Refreshing the screenshot

```
python tools/screenshot.py docs/img/app.png
```

It draws the window against `tools/sample.py`, so changing the look changes the picture in
the docs. `tests/test_docs.py` checks the picture is there.

## Changing the sheet format

1. Change `brainwaves/sheets/layout.py`. It holds the geometry and nothing else, and its
   docstring is the diagram.
2. Change `parse_card` and `card_block` in `brainwaves/sheets/week.py` together.
   `tests/test_week_sheet.py` checks they are inverses, which catches most mistakes.
3. Change `brainwaves/sheets/style.py` to match. One `updateCells` per day column carries
   the formatting, so a new field means a new branch in `_cell_format` and `_cell_for`.
4. Update [The sheets](sheets.md). The diagram there and the one in `layout.py` say the same
   thing; keep them that way.

Old sheets will not have the new field. Parsing is deliberately forgiving: a short row reads
as blank, an unknown risk reads as none, and a card with no id is given one.

## Changing the look

`brainwaves/palette.py` holds every colour, and both the window's stylesheet
(`app/theme.py`) and the Google Sheets formatting (`sheets/style.py`) read it, which is what
makes a card on the board and a card on the sheet look like the same object. Widgets ask for
a look by object name or dynamic property; no colour is chosen anywhere else.

Text sizes are named at the top of `app/theme.py`: `TEXT_*` for the window and the board,
`EDITOR_*` for the card editor. Every size in the stylesheet is one of them, so change a
number there and that text changes everywhere it appears. `TEXT_SCALE` makes all of them
bigger or smaller at once. Cards and day headings are a fixed size, so their text cannot
grow far before it is cut short. The editor and the panels have room to spare.

## Adding a field to a card

`model.CabinAct`, then the sheet (above), then `app/card.py` if it should show on the card,
then `app/editor.py` so it can be typed, then `sheets/support.py` if the Puppet Master needs
to see it. Add a case to `tests/test_week_sheet.py` and to `tests/test_app.py`.

## Releasing

```
git tag v0.2.0 && git push --tags
```

`.github/workflows/release.yml` runs `tools/build_settings.py` to put camp's Google client
and Skills doc into `brainwaves/built_in.py` from the repository's secrets, then builds the
one-file executable on Windows, macOS and Linux and attaches all three to a GitHub release.
`tools/build_icon.py` turns `icon.png` into each platform's icon first, and on Linux
`tools/build_linux_release.py` packs the executable, the icon and an `install.sh` that
writes a desktop entry into `brainwaves-linux.tar.gz`; `brainwaves.update` unpacks that
archive and installs the executable inside it.
That is what makes the download work with no config file; a source checkout leaves
`built_in.py` blank and reads a config file as before, and a test checks that camp's real
credentials never get committed. `brainwaves.update` finds the asset whose name
mentions the platform it is running on, so the file names matter: they come from
`brainwaves.spec`.

Pushing to `main` builds this site and deploys it to GitHub Pages
(`.github/workflows/docs.yml`). Enable Pages for the repository once, with the `gh-pages`
branch as source.
