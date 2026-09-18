"""Two cabins asking for the same thing at the same time.

Every cabin act runs in the same hour of the day, so two cabins on the same weekday cannot
both be at Low Ropes 1, and cannot both have Dylan. Finding those is arithmetic on a week
and nothing else, which is why it lives here rather than in the window.

A chip need not name a person. "Counselor" is any of twenty-two, "Canopy Tour" is any of the
fourteen checked off on it, and asking for one of those twice over is not a clash at all —
only asking for more of them than camp has. `StaffLists` is what says how many that is; with
no lists to hand, every chip counts as one person, which errs towards saying something.

A clash is reported, never prevented. The Brain may well want to see two cabins on the lake
and decide it is fine; what they must not do is find out on the day.
"""

from dataclasses import dataclass

from brainwaves.model import DAY_COLUMNS, Week
from brainwaves.names import normalize
from brainwaves.sheets.staff import StaffLists

LOCATION = "Location"
HERO = "HERO"

# Locations that say nothing about where a cabin will be, so two of them do not clash.
# These are compared after `normalize`, which is why "_Other" is written without its
# underscore.
VAGUE_LOCATIONS = frozenset({"other", "wandering"})


@dataclass(frozen=True)
class Conflict:
    """One thing more cabins have asked for on one day than there is of it."""

    kind: str
    what: str
    day: str
    column: int
    cabins: tuple[str, ...]
    cards: tuple[str, ...]
    available: int = 1

    @property
    def wanted(self) -> int:
        """How many cabins have asked."""
        return len(self.cabins)

    @property
    def summary(self) -> str:
        """The clash in one line, for a tooltip or a report."""
        who = _listed(self.cabins)
        if self.available > 1:
            return f"{self.day}: {who} want {self.what}, and only {self.available} can"
        return (
            f"{self.day}: {who} both want {self.what}"
            if self.wanted == 2
            else (f"{self.day}: {who} all want {self.what}")
        )


def find_conflicts(week: Week, staff: StaffLists | None = None) -> list[Conflict]:
    """Every clash of place or HERO on the week's days, in the order they are read.

    The Extra columns are left out: an activity with no day yet cannot clash with anything.
    """
    lists = staff or StaffLists()
    found: list[Conflict] = []
    for column in range(min(DAY_COLUMNS, len(week.days))):
        placed = week.day_cards(column)
        day = week.days[column].name
        found += _clashes(day, column, placed, LOCATION, _locations, lambda _what: 1)
        found += _clashes(day, column, placed, HERO, _heroes, lists.how_many)
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


def _listed(names) -> str:
    """Cabin names as a person would say them: M1 and P1, or M1, P1 and O1."""
    if len(names) < 3:
        return " and ".join(names)
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _clashes(day, column, placed, kind, wanted, supply) -> list[Conflict]:
    """Group a day's cards by what they asked for, and report what there is not enough of."""
    asked: dict[str, list] = {}
    spelling: dict[str, str] = {}
    for cabin, card in placed:
        for value in wanted(card):
            key = normalize(value)
            if not key:
                continue
            asked.setdefault(key, []).append((cabin, card))
            spelling.setdefault(key, value.strip())
    clashes = []
    for key, wanting in asked.items():
        available = supply(spelling[key])
        if len(wanting) <= available:
            continue
        clashes.append(
            Conflict(
                kind=kind,
                what=spelling[key],
                day=day,
                column=column,
                cabins=tuple(cabin.name for cabin, _ in wanting),
                cards=tuple(card.id for _, card in wanting),
                available=available,
            )
        )
    return clashes
