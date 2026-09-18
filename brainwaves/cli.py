"""The `brainwaves` command. Opening the window is what it mostly does."""

import argparse
import sys

from brainwaves import __version__
from brainwaves.config import load_config
from brainwaves.google import auth
from brainwaves.sheets.source import CsvWorkbook


def main(argv=None) -> int:
    """Run the command. Returns the process exit code."""
    parser = argparse.ArgumentParser(prog="brainwaves", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("app", help="open the window (the default)")
    commands.add_parser("sign-in", help="sign in to Google and save the result")
    commands.add_parser("sign-out", help="forget the saved Google sign-in")
    commands.add_parser("where", help="print where settings and saved state live")
    template = commands.add_parser(
        "template", help="write the blank week template, to Drive or to CSV files"
    )
    template.add_argument("--folder", help="Drive folder id to create the template sheet in")
    template.add_argument("--csv", help="folder to write the template to as CSV files instead")
    template.add_argument("--session", type=int, default=0)
    template.add_argument("--week", type=int, default=0)
    arguments = parser.parse_args(argv)

    config = load_config()
    if arguments.command == "sign-out":
        auth.sign_out()
        print("Signed out.")
        return 0
    if arguments.command == "where":
        return _where(config)
    if arguments.command == "sign-in":
        return _sign_in(config)
    if arguments.command == "template":
        return _template(config, arguments)

    from brainwaves.app.main import run_app

    return run_app(config)


def _where(config) -> int:
    """Say where the settings came from, which is the first question when something is off."""
    from brainwaves.config import config_paths

    found = [path for path in config_paths() if path.exists()]
    print("settings file  " + (str(found[-1]) if found else "none, which is usually right"))
    if not found:
        print(f"               (one would be read from {config_paths()[-1]})")
    print(
        "google client  " + ("set up" if config.has_client else "MISSING - see the install guide")
    )
    print("skills doc     " + (config.skills_sheet or "not set; HERO chips will be free text"))
    print(f"sign-in        {auth.token_file()}")
    return 0


def _template(config, arguments) -> int:
    from brainwaves.defaults import DEFAULT_CABINS, DEFAULT_LOCATIONS
    from brainwaves.model import Cabin, Week, WeekId, sort_cabins
    from brainwaves.workspace import write_template

    week_id = WeekId(arguments.session or 0, arguments.week or 0)
    week = Week(week_id, cabins=sort_cabins(Cabin(name) for name in DEFAULT_CABINS))
    if arguments.csv:
        from pathlib import Path

        folder = Path(arguments.csv)
        folder.mkdir(parents=True, exist_ok=True)
        workbook = _CsvTemplate(folder)
        write_template(workbook, week, DEFAULT_LOCATIONS)
        print(f"Wrote the template to {folder}")
        return 0
    if not arguments.folder:
        print("Give --folder <drive folder id> or --csv <folder>", file=sys.stderr)
        return 1
    credentials = auth.saved_credentials()
    if credentials is None:
        print("Run `brainwaves sign-in` first.", file=sys.stderr)
        return 1
    from brainwaves.workspace import Workspace

    sheet = Workspace(credentials, config).create_week(arguments.folder, week_id, None)
    print(f"Created {sheet.workbook.title}")
    return 0


class _CsvTemplate(CsvWorkbook):
    """A CSV workbook that answers the two spreadsheet questions `write_template` asks."""

    class _Sheet1:
        def update_title(self, title) -> None:
            """CSV files are named by tab already."""

    @property
    def spreadsheet(self):
        """Stands in for the gspread spreadsheet."""
        return type("Spreadsheet", (), {"sheet1": self._Sheet1()})()

    def tab_id(self, tab: str) -> int:
        """Formatting is discarded, so any id will do."""
        return 0


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
