"""The Support Requests tab: what each day asks of staff outside the cabin.

It is derived, never edited. Brain Waves rewrites it whenever the board changes, which is
the point: the Puppet Master reads one tab instead of every card.
"""

from brainwaves.model import DAY_COLUMNS, Week
from brainwaves.names import join_list
from brainwaves.sheets.source import Table

HEADER = ["Cabin", "Activity", "Location", "Risk", "HEROES", "Van", "Armory", "Picnic", "Food"]
TICK = "✓"


def render_support(week: Week) -> Table:
    """One block per weekday, listing the cards that need something."""
    table: Table = [[f"Support Requests - {week.id}"], []]
    for column in range(DAY_COLUMNS):
        day = week.days[column]
        table.append([day.name, day.subtitle])
        table.append(list(HEADER))
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
            ]
            for cabin, card in week.day_cards(column)
            if card.needs_support
        ]
        table.extend(rows or [["Nothing needed"]])
        table.append([])
    return table


def _tick(flag: bool) -> str:
    return TICK if flag else ""
