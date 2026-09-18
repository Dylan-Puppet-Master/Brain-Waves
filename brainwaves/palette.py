"""One palette, used by the desktop window and by the Google Sheets template.

Keeping both in one place is what makes a card on the board and a card on the sheet look
like the same object.
"""

INK = "#1f2933"
MUTED = "#6b7785"
FAINT = "#9aa5b1"
SURFACE = "#ffffff"
PANEL = "#f4f6f8"
SUNKEN = "#e9edf1"
LINE = "#dbe1e8"
ACCENT = "#0f766e"
ACCENT_SOFT = "#e3f1ef"
ACCENT_DARK = "#0b5a54"
WARN = "#b45309"
CLASH = "#c0392b"  # two cabins wanting the same thing at the same time

VILLAGE_COLORS = {
    "Pine": ("#3f7a4e", "#e8f2eb"),
    "Cedar": ("#96602f", "#f4ece3"),
    "Manzi": ("#b0457a", "#fbe9f1"),
    "Oak": ("#6b57b5", "#eeeaf8"),
}

RISK_COLORS = {
    "R": "#c0392b",
    "Y": "#d98e04",
    "G": "#2e7d32",
    "N": "#9aa5b1",
}

RISK_LABELS = {
    "R": "Red - director sign-off",
    "Y": "Yellow - risk-managed",
    "G": "Green - trained facilitator",
    "N": "None",
}


def sheets_color(hex_color: str) -> dict[str, float]:
    """A "#rrggbb" string as the Sheets API's red/green/blue floats."""
    text = hex_color.lstrip("#")
    return {
        "red": int(text[0:2], 16) / 255,
        "green": int(text[2:4], 16) / 255,
        "blue": int(text[4:6], 16) / 255,
    }


def village_colors(village: str) -> tuple[str, str]:
    """Line and fill colors for a village, falling back to the neutral pair."""
    return VILLAGE_COLORS.get(village, (MUTED, PANEL))
