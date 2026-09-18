"""Staff names, read from the same Skills doc Puppet Strings reads.

Only the names matter here: they are what a HERO chip may hold, so that a chip on a card
and a name in a request mean the same person. The Skills tab keeps three header rows and
then one row per staff member, whose name is the first cell.
"""

from brainwaves.sheets.source import Table

HEADER_ROWS = 3
NAME_COLUMN = 0


def parse_staff_names(table: Table) -> tuple[str, ...]:
    """Every staff name on the Skills tab, in sheet order, without duplicates."""
    names: list[str] = []
    for row in table[HEADER_ROWS:]:
        name = row[NAME_COLUMN].strip() if row else ""
        if name and name not in names:
            names.append(name)
    return tuple(names)
