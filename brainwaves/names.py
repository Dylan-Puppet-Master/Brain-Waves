"""Identifiers: how a piece of text becomes a stable, comparable name."""

import re
import unicodedata
from uuid import uuid4

WORD = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    """Lowercase, accent-free, underscore-joined form of `text`, for comparing names."""
    stripped = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return WORD.sub("_", stripped.lower()).strip("_")


def new_card_id() -> str:
    """A fresh card id. Short enough to read in a sheet cell, long enough not to collide."""
    return uuid4().hex[:12]


def split_list(value: str) -> tuple[str, ...]:
    """A comma-separated cell as a tuple of stripped items."""
    return tuple(item.strip() for item in value.split(",") if item.strip())


def join_list(items) -> str:
    """The inverse of `split_list`."""
    return ", ".join(items)
