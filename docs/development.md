# Development

## Layout

```
brainwaves/
  model.py, names.py, palette.py     domain objects, identifiers, the shared colours
  config.py, defaults.py             config.toml and saved state, what a new week starts with
  sheets/                            layout, parse and render, formatting, Support Requests, staff names
  google/                            auth, Drive, Drive comments, retrying a wobble
  comments.py                        matching Drive threads to cards
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

A poll calls `Workspace.read_board`, which reads the Board tab alone and keeps the cabins
and locations already in hand. `Workspace.read` reads everything and is what opening a week
and pressing Refresh do.

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

## Adding a field to a card

`model.CabinAct`, then the sheet (above), then `app/card.py` if it should show on the card,
then `app/editor.py` so it can be typed, then `sheets/support.py` if the Puppet Master needs
to see it. Add a case to `tests/test_week_sheet.py` and to `tests/test_app.py`.

## Releasing

```
git tag v0.2.0 && git push --tags
```

`.github/workflows/release.yml` builds the one-file executable on Windows, macOS and Linux
and attaches all three to a GitHub release. `brainwaves.update` finds the asset whose name
mentions the platform it is running on, so the file names matter: they come from
`brainwaves.spec`.

Pushing to `main` builds this site and deploys it to GitHub Pages
(`.github/workflows/docs.yml`). Enable Pages for the repository once, with the `gh-pages`
branch as source.
