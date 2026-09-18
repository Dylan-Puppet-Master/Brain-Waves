"""Two cabins asking for the same thing at the same time.

Every cabin act runs in the same hour of the day, so two cabins on the same weekday cannot
both be at Low Ropes 1, and cannot both have Dylan. Finding those is arithmetic on a week
and nothing else, which is why it lives here rather than in the window.

A clash is reported, never prevented. The Brain may well want to see two cabins on the lake
and decide it is fine; what they must not do is find out on the day.
"""

from dataclasses import dataclass

from brainwaves.model import DAY_COLUMNS, Week
from brainwaves.names import normalize

LOCATION = "Location"
HERO = "HERO"

# Locations that say nothing about where a cabin will be, so two of them do not clash.
# These are compared after `normalize`, which is why "_Other" is written without its
# underscore.
VAGUE_LOCATIONS = frozenset({"other", "wandering"})


@dataclass(frozen=True)
class Conflict:
    """One thing two or more cabins have both asked for on one day."""

    kind: str
    what: str
    day: str
    column: int
    cabins: tuple[str, ...]
    cards: tuple[str, ...]

    @property
    def summary(self) -> str:
        """The clash in one line, for a tooltip or a report."""
        return f"{self.day}: {' and '.join(self.cabins)} both want {self.what}"


def find_conflicts(week: Week) -> list[Conflict]:
    """Every clash of location or HERO on the week's days, in the order they are read.

    The Extra columns are left out: an activity with no day yet cannot clash with anything.
    """
    found: list[Conflict] = []
    for column in range(min(DAY_COLUMNS, len(week.days))):
        placed = week.day_cards(column)
        day = week.days[column].name
        found += _clashes(day, column, placed, LOCATION, _locations)
        found += _clashes(day, column, placed, HERO, _heroes)
    return found


def cards_in(conflicts) -> set[str]:
    """Every card mentioned by any of these clashes."""
    return {card for conflict in conflicts for card in conflict.cards}


def _locations(card) -> list[str]:
    if not card.location or normalize(card.location) in VAGUE_LOCATIONS:
        return []
    return [card.location]


def _heroes(card) -> list[str]:
    return list(card.heroes)


def _clashes(day: str, column: int, placed, kind: str, wanted) -> list[Conflict]:
    """Group a day's cards by what they asked for, and report anything asked for twice."""
    asked: dict[str, list] = {}
    spelling: dict[str, str] = {}
    for cabin, card in placed:
        for value in wanted(card):
            key = normalize(value)
            if not key:
                continue
            asked.setdefault(key, []).append((cabin, card))
            spelling.setdefault(key, value.strip())
    return [
        Conflict(
            kind=kind,
            what=spelling[key],
            day=day,
            column=column,
            cabins=tuple(cabin.name for cabin, _ in wanting),
            cards=tuple(card.id for _, card in wanting),
        )
        for key, wanting in asked.items()
        if len(wanting) > 1
    ]
