"""Two cabins asking for the same thing at the same time.

Every cabin act runs in the same hour of the day, so two cabins on the same weekday cannot
both be at Low Ropes 1, and cannot both have Dylan. The exception is an act whose title
begins "RH", which happens at rest hour instead and so only clashes with other rest hour
acts. Finding those is arithmetic on a week and nothing else, which is why it lives here
rather than in the window.

A chip need not name a person. "Counselor" is any of twenty-two, "Canopy Tour" is any of the
fourteen checked off on it, and asking for one of those twice over is not a clash at all —
only asking for more of them than camp has. `StaffLists` is what says how many that is; with
no lists to hand, every chip counts as one person, which errs towards saying something.

A clash is reported, never prevented. The Brain may well want to see two cabins on the lake
and decide it is fine; what they must not do is find out on the day.
"""

import re
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

# "RH Swim" or "RH: Swim", but not "Rhythm" or "RHYTHM".
REST_HOUR = re.compile(r"\s*RH(?![A-Za-z])")


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
    rest_hour: bool = False

    @property
    def when(self) -> str:
        """The day, and the hour of it if that is rest hour."""
        return f"{self.day} rest hour" if self.rest_hour else self.day

    @property
    def wanted(self) -> int:
        """How many cabins have asked."""
        return len(self.cabins)

    @property
    def summary(self) -> str:
        """The clash in one line, for a tooltip or a report."""
        who = _listed(self.cabins)
        if self.available > 1:
            return f"{self.when}: {who} want {self.what}, and only {self.available} can"
        return (
            f"{self.when}: {who} both want {self.what}"
            if self.wanted == 2
            else (f"{self.when}: {who} all want {self.what}")
        )


def find_conflicts(week: Week, staff: StaffLists | None = None) -> list[Conflict]:
    """Every clash of place or HERO on the week's days, in the order they are read.

    The Extra columns are left out: an activity with no day yet cannot clash with anything.
    Rest hour acts are only weighed against each other, as are the acts in the usual hour.
    """
    lists = staff or StaffLists()
    found: list[Conflict] = []
    for column in range(min(DAY_COLUMNS, len(week.days))):
        day = week.days[column].name
        for rest_hour in (False, True):
            placed = [
                (cabin, card)
                for cabin, card in week.day_cards(column)
                if is_rest_hour(card) == rest_hour
            ]
            found += _clashes(day, column, placed, LOCATION, _locations, lambda _what: 1, rest_hour)
            found += _clashes(day, column, placed, HERO, _heroes, lists.how_many, rest_hour)
    return found


def is_rest_hour(card) -> bool:
    """Whether the act happens at rest hour, which its title says by beginning "RH"."""
    return bool(REST_HOUR.match(card.title))


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


def _clashes(day, column, placed, kind, wanted, supply, rest_hour) -> list[Conflict]:
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
                rest_hour=rest_hour,
            )
        )
    return clashes
