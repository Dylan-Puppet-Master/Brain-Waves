"""Domain objects. Everything else reads and writes these; none of them touch a network.

A week of cabin acts is a grid: one row per cabin, one column per weekday, plus overflow
columns to the right holding acts that have not been given a day yet.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum

from brainwaves.names import new_card_id

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
DAY_COLUMNS = len(WEEKDAYS)
MIN_OVERFLOW_COLUMNS = 3


class Village(Enum):
    """The four villages, in the order they are shown, keyed by the cabin name prefix."""

    PINE = ("P", "Pine", "younger boys")
    CEDAR = ("C", "Cedar", "older boys")
    MANZI = ("M", "Manzi", "younger girls")
    OAK = ("O", "Oak", "older girls")

    def __init__(self, prefix: str, label: str, description: str) -> None:
        self.prefix = prefix
        self.label = label
        self.description = description

    @classmethod
    def of(cls, cabin_name: str) -> "Village | None":
        """The village whose prefix starts `cabin_name`, or None if no village claims it."""
        letter = cabin_name[:1].upper()
        return next((v for v in cls if v.prefix == letter), None)


class Risk(Enum):
    """How much risk management a cabin act needs, in the vocabulary of the sheet."""

    RED = "R"
    GREEN = "G"
    YELLOW = "Y"
    NONE = "N"

    @classmethod
    def parse(cls, text: str) -> "Risk":
        """A risk cell, however it is written. Anything unrecognised reads as NONE."""
        first = text.strip().upper()[:1]
        return next((r for r in cls if r.value == first), cls.NONE)


@dataclass(frozen=True)
class Cabin:
    """One cabin: its name, who leads it, and which village it belongs to."""

    name: str
    counselor: str = ""
    co_counselor: str = ""

    @property
    def village(self) -> Village | None:
        """The village the cabin name places it in."""
        return Village.of(self.name)

    @property
    def label(self) -> str:
        """How the cabin is written on the sheet and down the side of the board."""
        who = " & ".join(part for part in (self.counselor, self.co_counselor) if part)
        return f"{self.name} - {who}" if who else self.name


@dataclass(frozen=True)
class CabinAct:
    """One cabin activity: the card the villages move around."""

    id: str = field(default_factory=new_card_id)
    title: str = ""
    description: str = ""
    materials: tuple[str, ...] = ()
    location: str = ""
    notes: str = ""
    risk: Risk = Risk.NONE
    van: bool = False
    armory: bool = False
    picnic: bool = False
    food: bool = False
    heroes: tuple[str, ...] = ()

    @property
    def is_blank(self) -> bool:
        """Whether the card holds nothing worth keeping."""
        return not any(
            (self.title, self.description, self.materials, self.location, self.notes, self.heroes)
        )

    @property
    def needs_support(self) -> bool:
        """Whether the card asks anything of staff outside the cabin."""
        return bool(self.heroes) or self.van or self.armory or self.picnic or self.food


@dataclass(frozen=True)
class Day:
    """A weekday column, with the subtitle that says what else is happening that day."""

    name: str
    subtitle: str = ""

    @property
    def label(self) -> str:
        """Day name and subtitle as one line."""
        return f"{self.name} - {self.subtitle}" if self.subtitle else self.name


@dataclass(frozen=True)
class WeekId:
    """Which session and week a sheet covers."""

    session: int
    week: int

    def __str__(self) -> str:
        return f"S{self.session}W{self.week}"

    @property
    def title(self) -> str:
        """The spreadsheet name for this week."""
        return f"Cabin Act Sorting - {self}"

    @classmethod
    def parse(cls, text: str) -> "WeekId | None":
        """Read "S2W1" out of a spreadsheet title, or None if it holds no such code."""
        code = text.strip().rsplit(" ", 1)[-1].upper()
        if not code.startswith("S") or "W" not in code:
            return None
        session, _, week = code[1:].partition("W")
        if not (session.isdigit() and week.isdigit()):
            return None
        return cls(int(session), int(week))


@dataclass(frozen=True)
class Comment:
    """One discussion thread about one card, held in Google Drive with the sheet."""

    id: str
    card_id: str
    author: str
    created: datetime
    text: str
    resolved: bool = False
    replies: tuple["Reply", ...] = ()

    @property
    def latest(self) -> datetime:
        """When the thread last moved."""
        return max([self.created, *(r.created for r in self.replies)])


@dataclass(frozen=True)
class Reply:
    """One message in a thread."""

    id: str
    author: str
    created: datetime
    text: str


@dataclass(frozen=True)
class Week:
    """A whole week of cabin acts: the grid, its headings, and the cards in it."""

    id: WeekId
    cabins: tuple[Cabin, ...] = ()
    days: tuple[Day, ...] = tuple(Day(name) for name in WEEKDAYS)
    cards: dict[tuple[str, int], CabinAct] = field(default_factory=dict)
    overflow_columns: int = MIN_OVERFLOW_COLUMNS

    @property
    def columns(self) -> int:
        """Weekday columns plus overflow columns."""
        return DAY_COLUMNS + self.overflow_columns

    def card(self, cabin: str, column: int) -> CabinAct | None:
        """The card in one slot, or None if the slot is empty."""
        return self.cards.get((cabin, column))

    def place(self, cabin: str, column: int, card: CabinAct | None) -> "Week":
        """A copy of the week with one slot set or cleared."""
        cards = dict(self.cards)
        if card is None or card.is_blank:
            cards.pop((cabin, column), None)
        else:
            cards[cabin, column] = card
        return replace(self, cards=cards)

    def swap(self, cabin: str, one: int, other: int) -> "Week":
        """A copy of the week with two slots in the same cabin row exchanged."""
        cards = dict(self.cards)
        first, second = cards.pop((cabin, one), None), cards.pop((cabin, other), None)
        if first is not None:
            cards[cabin, other] = first
        if second is not None:
            cards[cabin, one] = second
        return replace(self, cards=cards)

    def row(self, cabin: str) -> dict[int, CabinAct]:
        """Every card belonging to one cabin, by column."""
        return {column: card for (name, column), card in self.cards.items() if name == cabin}

    def day_cards(self, column: int) -> list[tuple[Cabin, CabinAct]]:
        """Every card in one weekday column, in cabin order."""
        found = []
        for cabin in self.cabins:
            card = self.card(cabin.name, column)
            if card is not None:
                found.append((cabin, card))
        return found

    def locate(self, card_id: str) -> tuple[str, int] | None:
        """Which slot a card sits in, or None if it is no longer on the board."""
        return next((slot for slot, card in self.cards.items() if card.id == card_id), None)


def sort_cabins(cabins) -> tuple[Cabin, ...]:
    """Cabins grouped by village in village order, and by name within a village."""
    order = {village: index for index, village in enumerate(Village)}
    return tuple(sorted(cabins, key=lambda c: (order.get(c.village, len(order)), c.name)))
