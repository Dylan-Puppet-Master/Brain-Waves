"""Where Brain Waves gets its settings, and what it remembers for you.

Settings come from three places, each overriding the one before:

1. `brainwaves.built_in`, which the release build fills in with camp's Google client and
   Skills doc. A village leader who downloads Brain Waves therefore has to set up nothing.
2. `brainwaves.toml` beside the program, for changing something on one machine without a
   new release.
3. `config.toml` in the usual per-user config folder, which is what a source checkout uses.

State — the Drive folder, the session and the week — lives in `state.json` beside the saved
sign-in, and is the only part of this that differs from one person to the next.
"""

import json
import os
import sys
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from platformdirs import user_config_path, user_data_path

from brainwaves.defaults import CATEGORIES_SHEET, SKILLS_SHEET

APP_NAME = "brainwaves"

DEFAULT_SKILLS_TAB = "Skills"
DEFAULT_CATEGORIES_TAB = "Categories"
DEFAULT_POLL_SECONDS = 3
DEFAULT_COMMENT_POLL_SECONDS = 10
DEFAULT_RELEASES = "https://api.github.com/repos/Dylan-Puppet-Master/Brain-Waves/releases/latest"


@dataclass(frozen=True)
class Config:
    """What Brain Waves needs to reach Google and the Skills doc.

    `poll_seconds` is how often to read the board, the cabins and the locations, which is
    one request. `comment_poll_seconds` is how often to read the comments, which live in
    Drive and change far less often.
    """

    client_id: str = ""
    client_secret: str = ""
    skills_sheet: str = SKILLS_SHEET
    skills_tab: str = DEFAULT_SKILLS_TAB
    categories_sheet: str = CATEGORIES_SHEET
    categories_tab: str = DEFAULT_CATEGORIES_TAB
    poll_seconds: int = DEFAULT_POLL_SECONDS
    comment_poll_seconds: int = DEFAULT_COMMENT_POLL_SECONDS
    releases_url: str = DEFAULT_RELEASES

    @property
    def has_client(self) -> bool:
        """Whether an OAuth client has been configured, without which sign-in cannot start."""
        return bool(self.client_id and self.client_secret)


@dataclass(frozen=True)
class State:
    """What the app remembers between runs."""

    folder_id: str = ""
    folder_name: str = ""
    session: int = 1
    week: int = 1


def program_folder() -> Path:
    """The folder Brain Waves is running from: beside the downloaded file, or the checkout."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_paths() -> list[Path]:
    """Every file that may hold settings, in the order they override one another."""
    override = os.environ.get("BRAINWAVES_CONFIG")
    if override:
        return [Path(override).expanduser()]
    return [
        program_folder() / f"{APP_NAME}.toml",
        user_config_path(APP_NAME) / "config.toml",
    ]


def config_path() -> Path:
    """The settings file in use, or where one would be looked for if none exists."""
    found = [path for path in config_paths() if path.exists()]
    return found[-1] if found else config_paths()[-1]


def data_path(name: str) -> Path:
    """A file in the app's data folder, whose folder is created on demand."""
    override = os.environ.get("BRAINWAVES_DATA")
    folder = Path(override).expanduser() if override else user_data_path(APP_NAME)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name


def load_config(path: Path | None = None) -> Config:
    """Read the settings, starting from what was built in and letting files override it."""
    data = _built_in()
    for candidate in [path] if path else config_paths():
        if candidate and candidate.exists():
            _merge(data, tomllib.loads(candidate.read_text(encoding="utf-8")))
    google = data.get("google", {})
    sheets = data.get("sheets", {})
    sync = data.get("sync", {})
    return Config(
        client_id=google.get("client_id", ""),
        client_secret=google.get("client_secret", ""),
        skills_sheet=sheets.get("skills", SKILLS_SHEET),
        skills_tab=sheets.get("skills_tab", DEFAULT_SKILLS_TAB),
        categories_sheet=sheets.get("categories", CATEGORIES_SHEET),
        categories_tab=sheets.get("categories_tab", DEFAULT_CATEGORIES_TAB),
        poll_seconds=int(sync.get("poll_seconds", DEFAULT_POLL_SECONDS)),
        comment_poll_seconds=int(sync.get("comment_poll_seconds", DEFAULT_COMMENT_POLL_SECONDS)),
        releases_url=data.get("updates", {}).get("releases_url", DEFAULT_RELEASES),
    )


def _built_in() -> dict:
    """What the release build put in, shaped like the config file."""
    from brainwaves.built_in import SETTINGS

    return {
        "google": {
            "client_id": SETTINGS.get("client_id", ""),
            "client_secret": SETTINGS.get("client_secret", ""),
        },
        "sheets": {
            key: value
            for key, value in (
                ("skills", SETTINGS.get("skills_sheet", "")),
                ("categories", SETTINGS.get("categories_sheet", "")),
            )
            if value
        },
    }


def _merge(into: dict, extra: dict) -> None:
    """Overlay one config's sections onto another, a setting at a time."""
    for section, values in extra.items():
        if isinstance(values, dict):
            into.setdefault(section, {}).update(values)


def load_state() -> State:
    """Read the remembered folder, session and week."""
    path = data_path("state.json")
    if not path.exists():
        return State()
    try:
        return State(**{**asdict(State()), **json.loads(path.read_text(encoding="utf-8"))})
    except (ValueError, TypeError):
        return State()


def save_state(state: State) -> None:
    """Write the remembered folder, session and week."""
    data_path("state.json").write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")


def with_week(state: State, session: int, week: int) -> State:
    """The state, pointed at another week."""
    return replace(state, session=session, week=week)
