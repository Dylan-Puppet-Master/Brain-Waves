# Brain Waves

Brain Waves is a software tool to help Village Leaders plan Cabin Activities. It is essentially an alternate frontend to Google Sheets with various quality-of-life improvements added in. Village Leaders are free to continue using Google Sheets if they want -- all the information (including comments) will update in almost-real-time within Brain Waves.

The creation of Brain Waves was motivated by a wish and a wonder.

**The wish** for the ability to simply drag, drop, and swap cabin acts across the week. The current system of sorting cabin acts is, in my opinion, unnecessarilly tedious and not what Google Sheets was designed for.

**The wonder** of how possible it would be to consolidate all staff scheduling -- including HERO scheduling -- under one Puppet Master system. With progress being made towards automating the staff schedule (see [Puppet Strings](https://github.com/Dylan-Puppet-Master/Puppet-Strings)), it would be extremely convenient for cabin activity staffing requests to be in a standardized format.

**Surprise!** Brain Waves solves both of these problems and then some, with the only techincal drawback being slightly higher latencies in real-time collaboration. 

![The board](docs/img/app.png)


## Where things live

| Thing | Where |
|---|---|
| One week of cabin acts | A Google spreadsheet named `Cabin Act Sorting - S2W1` |
| Every week of a summer | One Google Drive folder, which you pick once |
| Staff names for the HERO chips | The Skills doc, the same one Puppet Strings reads |
| Your sign-in, folder and week | Your own computer, so the program opens where you left it |
| The code | This repository, one Python package |

Start with [Install and set up](install.md).


Full documentation: the `docs/` folder, published with MkDocs to GitHub Pages.

## How it fits together

| Module | Does |
|---|---|
| `brainwaves/model.py` | Cabin, CabinAct, Day, Week, Comment, and the moves on a week |
| `brainwaves/sheets/` | The Board format: geometry, parse, render, formatting, derived tabs |
| `brainwaves/google/` | Sign-in, Drive browsing, Drive comments |
| `brainwaves/comments.py` | Which card a Drive thread is about |
| `brainwaves/conflicts.py` | Two cabins wanting one place or one HERO on one day |
| `brainwaves/workspace.py` | Finding, opening and creating week sheets |
| `brainwaves/store.py` | One loaded week, every change to it, and the queue of writes |
| `brainwaves/app/` | The desktop window |
| `brainwaves/cli.py` | The `brainwaves` command |

## Install

Village leaders download one file from the
[releases page](https://github.com/camp-augusta/brainwaves/releases) and open it. There is
nothing else to install and no config file to place: camp's Google client and Skills doc
are built into the release, and the only per-person settings — the sign-in, the folder and
the week — are remembered by the program. From source:

```
git clone https://github.com/camp-augusta/brainwaves
cd brainwaves
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
brainwaves
```

Then follow `docs/install.md` to create the Google OAuth client, write
`~/.config/brainwaves/config.toml`, and link the Drive folder that holds the week sheets.

## Use

```
brainwaves                                  # open the window
brainwaves sign-in                          # sign in to Google without the window
brainwaves where                            # which settings are in use, and where the sign-in lives
brainwaves template --csv /tmp/template     # write the blank week template out as CSV
brainwaves template --folder <drive id>     # create a blank week sheet in a Drive folder
```

## Develop

```
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
mkdocs serve
python tools/screenshot.py docs/img/app.png
```

The test suite runs entirely offline; `tests/fakes.py` stands in for Google.
