"""How the week's demands fall across its days, for spreading them out evenly.

Each measure counts something a cabin act asks of staff outside the cabin, day by day.
Only the weekday columns count: an act in Extra has not been given a day, so it loads
none of them, but the number waiting there is kept so nobody forgets it.
"""

from collections.abc import Callable
from dataclasses import dataclass

from brainwaves.model import DAY_COLUMNS, CabinAct, Week


@dataclass(frozen=True)
class Measure:
    """One thing to count, and how to say it."""

    key: str
    title: str  # the tab
    unit: str  # one of them
    units: str  # more than one
    count: Callable[[CabinAct], int]
    names: Callable[[CabinAct], tuple[str, ...]] = lambda card: ()  # what was counted, by name

    def say(self, value: float) -> str:
        """A count with its unit, singular or plural to match."""
        number = f"{value:g}" if value == int(value) else f"{value:.1f}"
        return f"{number} {self.unit if value == 1 else self.units}"


MEASURES = (
    Measure(
        "heroes",
        "HEROes",
        "HERO",
        "HEROes",
        lambda card: len(card.heroes),
        lambda card: card.heroes,
    ),
    Measure("food", "Food", "food act", "food acts", lambda card: int(card.food)),
    Measure("van", "Van", "van act", "van acts", lambda card: int(card.van)),
    Measure("armory", "Armory", "armory act", "armory acts", lambda card: int(card.armory)),
    Measure(
        "materials",
        "Materials",
        "material",
        "materials",
        lambda card: len(card.materials),
        lambda card: card.materials,
    ),
)


@dataclass(frozen=True)
class Contribution:
    """One card's share of one day's count."""

    cabin: str
    title: str
    count: int
    names: tuple[str, ...] = ()


@dataclass(frozen=True)
class DayLoad:
    """One measure on one weekday: the total and the cards that make it up."""

    total: int
    parts: tuple[Contribution, ...]


@dataclass(frozen=True)
class Spread:
    """One measure across the whole week."""

    measure: Measure
    days: tuple[DayLoad, ...]
    unplaced: int  # counted on cards that have no day yet

    @property
    def totals(self) -> list[int]:
        """The count for each weekday, Monday first."""
        return [day.total for day in self.days]

    @property
    def total(self) -> int:
        """The count across every weekday."""
        return sum(self.totals)

    @property
    def even_share(self) -> float:
        """What each day would carry if the week were perfectly level."""
        return self.total / len(self.days) if self.days else 0.0

    @property
    def busiest(self) -> tuple[int, ...]:
        """The weekdays carrying the most, or none if nothing is counted at all."""
        return self._days_at(max(self.totals, default=0))

    @property
    def quietest(self) -> tuple[int, ...]:
        """The weekdays carrying the least, or none if nothing is counted at all."""
        return self._days_at(min(self.totals, default=0))

    def _days_at(self, value: int) -> tuple[int, ...]:
        if not self.total:
            return ()
        return tuple(index for index, total in enumerate(self.totals) if total == value)

    @property
    def gap(self) -> int:
        """How far apart the busiest and quietest days are."""
        return max(self.totals, default=0) - min(self.totals, default=0)


def spread(week: Week, measure: Measure) -> Spread:
    """Count one measure across the weekdays of a week."""
    days = []
    for column in range(DAY_COLUMNS):
        parts = tuple(
            Contribution(
                cabin.name, card.title or "Untitled", measure.count(card), measure.names(card)
            )
            for cabin, card in week.day_cards(column)
            if measure.count(card)
        )
        days.append(DayLoad(sum(part.count for part in parts), parts))
    unplaced = sum(
        measure.count(card) for (_, column), card in week.cards.items() if column >= DAY_COLUMNS
    )
    return Spread(measure, tuple(days), unplaced)


def spreads(week: Week) -> list[Spread]:
    """Every measure across the week, in the order they are shown."""
    return [spread(week, measure) for measure in MEASURES]
