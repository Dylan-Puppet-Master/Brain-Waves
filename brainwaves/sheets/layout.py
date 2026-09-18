"""The geometry of the Board tab: where every cabin, day and card field sits.

The board is a grid of card blocks. Reading down a block you see the same five labels a
Google Sheets user has always seen; reading across, the value column is wide and the flag
columns are narrow. One further column per block holds the card's id and is hidden, so a
card keeps its comments when it moves.

    A            B             C            D         E        F (hidden)
  ┌──────────┬─────────────────────────┬──────────┬────────┬──────────┐
  │          │ Monday                                      │          │  day name
  │          │ Coco's Day                                  │          │  day subtitle
  ├──────────┼─────────────┬───────────┼──────────┼────────┼──────────┤
  │ M1       │ Becoming a team <3      │ Van      │ ☐      │ 9f2a1c…  │
  │ Jana     │ Description │ Do low r… │ Risk     │ N      │          │
  │          │ Materials   │ rope, …   │ Armory   │ ☐      │          │
  │          │ Location    │ Low Ropes │ Picnic   │ ☐      │          │
  │          │ Notes       │ …         │ Food     │ ☐      │          │
  │          │ HEROES      │ Dylan, Vic                    │          │
  └──────────┴─────────────────────────┴──────────┴────────┴──────────┘
"""

TITLE_ROW = 0
DAY_ROW = 1
SUBTITLE_ROW = 2
FIRST_CARD_ROW = 3

CABIN_COLUMN = 0
FIRST_CARD_COLUMN = 1

CARD_ROWS = 6
CARD_COLUMNS = 5
VISIBLE_CARD_COLUMNS = 4
ID_OFFSET = 4

# Row offsets within a card block.
TITLE, DESCRIPTION, MATERIALS, LOCATION, NOTES, HEROES = range(CARD_ROWS)

FIELD_LABELS = ("", "Description", "Materials", "Location", "Notes", "HEROES")
FLAG_LABELS = ("Van", "Risk", "Armory", "Picnic", "Food")

LABEL_OFFSET = 0
VALUE_OFFSET = 1
FLAG_LABEL_OFFSET = 2
FLAG_VALUE_OFFSET = 3


def card_origin(cabin_index: int, column: int) -> tuple[int, int]:
    """The top-left cell of a card block, as zero-based row and column."""
    return (
        FIRST_CARD_ROW + cabin_index * CARD_ROWS,
        FIRST_CARD_COLUMN + column * CARD_COLUMNS,
    )


def column_origin(column: int) -> int:
    """The first column of a day or overflow block."""
    return FIRST_CARD_COLUMN + column * CARD_COLUMNS


def cabin_row(cabin_index: int) -> int:
    """The first row of a cabin's band."""
    return FIRST_CARD_ROW + cabin_index * CARD_ROWS


def grid_size(cabins: int, columns: int) -> tuple[int, int]:
    """Rows and columns the whole board occupies."""
    return FIRST_CARD_ROW + cabins * CARD_ROWS, FIRST_CARD_COLUMN + columns * CARD_COLUMNS
