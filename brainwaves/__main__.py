"""Entry point for `python -m brainwaves` and for the packaged executable."""

from brainwaves.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
