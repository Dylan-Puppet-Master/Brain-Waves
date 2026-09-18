"""Put camp's settings into the copy about to be packaged.

    GOOGLE_CLIENT_ID=… GOOGLE_CLIENT_SECRET=… SKILLS_SHEET=… python tools/build_settings.py

The release workflow runs this from the repository's secrets before PyInstaller, so the
downloaded file signs in and finds the Skills doc with nothing for a village leader to set
up. Run it by hand only when building a release yourself; it rewrites `built_in.py`, which
is meant to stay blank in the repository.
"""

import os
import sys
from pathlib import Path

BUILT_IN = Path(__file__).resolve().parent.parent / "brainwaves" / "built_in.py"
WANTED = {
    "client_id": "GOOGLE_CLIENT_ID",
    "client_secret": "GOOGLE_CLIENT_SECRET",
    "skills_sheet": "SKILLS_SHEET",
}


def main() -> int:
    """Rewrite the settings dict, keeping the module's docstring. Returns the exit code."""
    settings = {name: os.environ.get(variable, "") for name, variable in WANTED.items()}
    missing = [variable for name, variable in WANTED.items() if not settings[name]]
    if missing:
        print(f"Not set: {', '.join(missing)}", file=sys.stderr)
        print("The build will need a config.toml on each machine.", file=sys.stderr)
        return 1
    source = BUILT_IN.read_text(encoding="utf-8")
    docstring, _, _ = source.partition("SETTINGS: dict[str, str] =")
    lines = "\n".join(f'    "{name}": "{value}",' for name, value in settings.items())
    BUILT_IN.write_text(f"{docstring}SETTINGS: dict[str, str] = {{\n{lines}\n}}\n", "utf-8")
    print(f"Built camp's settings into {BUILT_IN.name}: {', '.join(settings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
