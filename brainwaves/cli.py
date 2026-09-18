"""The `brainwaves` command. Opening the window is what it mostly does."""

import argparse
import sys

from brainwaves import __version__
from brainwaves.config import config_path, load_config
from brainwaves.google import auth


def main(argv=None) -> int:
    """Run the command. Returns the process exit code."""
    parser = argparse.ArgumentParser(prog="brainwaves", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("app", help="open the window (the default)")
    commands.add_parser("sign-in", help="sign in to Google and save the result")
    commands.add_parser("sign-out", help="forget the saved Google sign-in")
    commands.add_parser("where", help="print where settings and saved state live")
    arguments = parser.parse_args(argv)

    config = load_config()
    if arguments.command == "sign-out":
        auth.sign_out()
        print("Signed out.")
        return 0
    if arguments.command == "where":
        print(f"config   {config_path()}")
        print(f"sign-in  {auth.token_file()}")
        return 0
    if arguments.command == "sign-in":
        return _sign_in(config)

    from brainwaves.app.main import run_app

    return run_app(config)


def _sign_in(config) -> int:
    try:
        credentials = auth.sign_in(config)
    except auth.AuthError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Signed in as {auth.account_email(credentials) or 'your Google account'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
