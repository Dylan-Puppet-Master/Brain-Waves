"""Signing in to Google as the user, once, and remembering it.

Brain Waves acts as the person using it: a comment they write is theirs, and a sheet they
cannot open stays closed. That needs an OAuth client, which camp creates once and puts in
`config.toml`; see docs/install.md.
"""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from brainwaves.config import Config, data_path

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


class AuthError(Exception):
    """Sign-in could not be completed. The message says what to do about it."""


def token_file() -> Path:
    """Where the saved sign-in lives."""
    return data_path("token.json")


def saved_credentials() -> Credentials | None:
    """The saved sign-in, refreshed if it has expired, or None if there is none to use."""
    path = token_file()
    if not path.exists():
        return None
    try:
        credentials = Credentials.from_authorized_user_file(str(path), SCOPES)
    except ValueError:
        return None
    if credentials.valid:
        return credentials
    if not (credentials.expired and credentials.refresh_token):
        return None
    try:
        credentials.refresh(Request())
    except Exception:  # noqa: BLE001 - any refresh failure means signing in again
        return None
    _save(credentials)
    return credentials


def sign_in(config: Config) -> Credentials:
    """Open the browser, ask for consent, and save the result. Raises AuthError."""
    if not config.has_client:
        raise AuthError(
            "No Google OAuth client in config.toml. See the install guide: a camp "
            "administrator creates one desktop client and puts its id and secret under "
            "[google]."
        )
    flow = InstalledAppFlow.from_client_config(_client_config(config), SCOPES)
    try:
        credentials = flow.run_local_server(port=0, prompt="consent")
    except Exception as e:  # noqa: BLE001 - the browser half of this can fail many ways
        raise AuthError(f"Google sign-in did not finish: {e}") from e
    _save(credentials)
    return credentials


def sign_out() -> None:
    """Forget the saved sign-in."""
    token_file().unlink(missing_ok=True)


def account_email(credentials: Credentials) -> str:
    """The signed-in address, or an empty string if Google did not say."""
    from googleapiclient.discovery import build

    try:
        service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
        return service.userinfo().get().execute().get("email", "")
    except Exception:  # noqa: BLE001 - the address is a nicety, never a blocker
        return ""


def _client_config(config: Config) -> dict:
    return {
        "installed": {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def _save(credentials: Credentials) -> None:
    token_file().write_text(credentials.to_json(), encoding="utf-8")
