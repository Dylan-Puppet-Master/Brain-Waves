"""The Support Requests tab: what each day asks of staff outside the cabin.

It is derived, never edited. Brain Waves rewrites it whenever the board changes, which is
the point: the Puppet Master reads one tab instead of every card.

`render_support` hands back the rows it has written as well as the table, so
`sheets.style` can format the day headings and column headings without working out the
same geometry a second time.
"""

from dataclasses import dataclass, field

from brainwaves.model import DAY_COLUMNS, Week
from brainwaves.names import join_list
from brainwaves.sheets.source import Table

HEADER = [
    "Cabin",
    "Activity",
    "Location",
    "Risk",
    "HEROES",
    "Van",
    "Armory",
    "Picnic",
    "Food",
    "Level 2 on Ground",
]
TICK = "✓"
NOTHING = "Nothing needed"


@dataclass
class SupportView:
    """The tab's cells, and which of its rows are headings."""

    table: Table = field(default_factory=list)
    day_rows: list[int] = field(default_factory=list)
    header_rows: list[int] = field(default_factory=list)
    quiet_rows: list[int] = field(default_factory=list)


def render_support(week: Week) -> SupportView:
    """One block per weekday, listing the cards that need something."""
    view = SupportView(table=[[f"Support Requests - {week.id}"], []])
    for column in range(DAY_COLUMNS):
        day = week.days[column]
        view.day_rows.append(len(view.table))
        view.table.append([day.name, day.subtitle])
        view.header_rows.append(len(view.table))
        view.table.append(list(HEADER))
        rows = [
            [
                cabin.label,
                card.title,
                card.location,
                card.risk.value,
                join_list(card.heroes),
                _tick(card.van),
                _tick(card.armory),
                _tick(card.picnic),
                _tick(card.food),
                _tick(card.level_two),
            ]
            for cabin, card in week.day_cards(column)
            if card.needs_support
        ]
        if not rows:
            view.quiet_rows.append(len(view.table))
            rows = [[NOTHING]]
        view.table.extend(rows)
        view.table.append([])
    return view


def _tick(flag: bool) -> str:
    return TICK if flag else ""
