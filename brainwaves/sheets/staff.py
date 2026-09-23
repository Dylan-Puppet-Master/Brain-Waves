"""Who a cabin act can ask for: a person, a category of person, or a skill.

Three lists, read from the two documents Puppet Strings already reads.

* **Names** are the staff on the Skills doc, so a chip and a Puppet Strings request mean
  the same person.
* **Categories** are the columns of the Staff Categories doc — Counselor, Director, VL —
  for when any one of them will do.
* **Skills** are the headings of the Skills doc — Canopy Tour, Lifeguard — for when anyone
  checked off on it will do.

Each list is kept with a count of how many people are in it, because that is what says
whether two cabins asking for a Lifeguard on one day is a problem or not.
"""

from dataclasses import dataclass, field
from functools import cached_property

from brainwaves.names import normalize
from brainwaves.sheets.source import Table

HEADER_ROWS = 3
NAME_COLUMN = 0
FIRST_SKILL_COLUMN = 3
SKILL_NAME_ROW = 1

PERSON = "person"
CATEGORY = "category"
SKILL = "skill"

# Headings that name no real group of people.
SKIPPED_HEADINGS = frozenset({"", "etc"})

# What a Skills cell says when somebody cannot actually do the thing yet.
NOT_YET = frozenset({"", ".", "past ex", "interested", "no", "-"})


@dataclass(frozen=True)
class StaffLists:
    """Everything a HERO chip may hold, and how many people each of them is."""

    names: tuple[str, ...] = ()
    categories: dict[str, int] = field(default_factory=dict)
    skills: dict[str, int] = field(default_factory=dict)

    @property
    def options(self) -> tuple[str, ...]:
        """Everything selectable, people first, then the groups they belong to."""
        return (*self.names, *sorted(self.categories), *sorted(self.skills))

    def kind_of(self, text: str) -> str:
        """Whether a chip names a person, a category, a skill — or, unknown, a person."""
        return self._kinds.get(normalize(text), PERSON)

    def how_many(self, text: str) -> int:
        """How many people could answer this chip. One, for a person or a name we do not know."""
        return max(self._counts.get(normalize(text), 1), 1)

    # Every chip on every card asks both questions each time the board is drawn, so the
    # answers are worked out once. A person's name wins over a category or skill spelled
    # the same, and a category over a skill.

    @cached_property
    def _kinds(self) -> dict[str, str]:
        kinds: dict[str, str] = {}
        for kind, names in (
            (SKILL, self.skills),
            (CATEGORY, self.categories),
            (PERSON, self.names),
        ):
            kinds.update((normalize(name), kind) for name in names)
        return kinds

    @cached_property
    def _counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for known in (self.skills, self.categories):
            counts.update((normalize(name), count) for name, count in known.items())
        return counts


def parse_staff_names(table: Table) -> tuple[str, ...]:
    """Every staff name on the Skills tab, in sheet order, without duplicates."""
    names: list[str] = []
    for row in table[HEADER_ROWS:]:
        name = row[NAME_COLUMN].strip() if row else ""
        if name and name not in names:
            names.append(name)
    return tuple(names)


def parse_skills(table: Table) -> dict[str, int]:
    """Skill name -> how many people are checked off on it.

    A skill spans several columns on the Skills tab, one per rank, and the ranks are Puppet
    Strings' business. Here a skill is just its heading, and somebody has it if any of its
    columns says anything other than that they have not got there yet.
    """
    if len(table) <= HEADER_ROWS:
        return {}
    headings = table[SKILL_NAME_ROW]
    columns: dict[str, list[int]] = {}
    for column in range(FIRST_SKILL_COLUMN, len(headings)):
        heading = headings[column].strip()
        if normalize(heading) in SKIPPED_HEADINGS:
            continue
        columns.setdefault(heading, []).append(column)
    return {
        heading: sum(1 for row in table[HEADER_ROWS:] if _has_skill(row, where))
        for heading, where in columns.items()
    }


def parse_categories(table: Table) -> dict[str, int]:
    """Category name -> how many people are in it. One column per category, members below."""
    if not table:
        return {}
    counts: dict[str, int] = {}
    for column, heading in enumerate(table[0]):
        heading = heading.strip()
        if normalize(heading) in SKIPPED_HEADINGS:
            continue
        members = sum(1 for row in table[1:] if column < len(row) and row[column].strip())
        counts[heading] = counts.get(heading, 0) + members
    return counts


def _has_skill(row, columns) -> bool:
    if not row or not row[NAME_COLUMN].strip():
        return False
    for column in columns:
        cell = row[column].strip().lower() if column < len(row) else ""
        if cell and cell not in NOT_YET:
            return True
    return False
