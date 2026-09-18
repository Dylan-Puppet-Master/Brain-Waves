"""Settings the user writes once, and state the app remembers for them.

Settings live in `config.toml` and name the Google OAuth client and the Skills doc. State
lives in `state.json` next to the cached token: which Drive folder holds the week sheets,
and which session and week were open last.
"""

import json
import os
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from platformdirs import user_config_path, user_data_path

APP_NAME = "brainwaves"

DEFAULT_SKILLS_TAB = "Skills"
DEFAULT_POLL_SECONDS = 3
DEFAULT_COMMENT_POLL_SECONDS = 10
DEFAULT_RELEASES = "https://api.github.com/repos/camp-augusta/brainwaves/releases/latest"


@dataclass(frozen=True)
class Config:
    """What Brain Waves needs to reach Google and the Skills doc.

    `poll_seconds` is how often to read the board, which is the tab people move cards on.
    `comment_poll_seconds` is how often to read the comments, the cabins and the locations,
    which change far less often.
    """

    client_id: str = ""
    client_secret: str = ""
    skills_sheet: str = ""
    skills_tab: str = DEFAULT_SKILLS_TAB
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


def config_path() -> Path:
    """Where `config.toml` is read from. `BRAINWAVES_CONFIG` overrides it."""
    override = os.environ.get("BRAINWAVES_CONFIG")
    if override:
        return Path(override).expanduser()
    return user_config_path(APP_NAME) / "config.toml"


def data_path(name: str) -> Path:
    """A file in the app's data folder, whose folder is created on demand."""
    override = os.environ.get("BRAINWAVES_DATA")
    folder = Path(override).expanduser() if override else user_data_path(APP_NAME)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name


def load_config(path: Path | None = None) -> Config:
    """Read the config file. A missing file yields defaults, which the app explains."""
    path = path or config_path()
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    google = data.get("google", {})
    sheets = data.get("sheets", {})
    sync = data.get("sync", {})
    return Config(
        client_id=google.get("client_id", ""),
        client_secret=google.get("client_secret", ""),
        skills_sheet=sheets.get("skills", ""),
        skills_tab=sheets.get("skills_tab", DEFAULT_SKILLS_TAB),
        poll_seconds=int(sync.get("poll_seconds", DEFAULT_POLL_SECONDS)),
        comment_poll_seconds=int(sync.get("comment_poll_seconds", DEFAULT_COMMENT_POLL_SECONDS)),
        releases_url=data.get("updates", {}).get("releases_url", DEFAULT_RELEASES),
    )


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
