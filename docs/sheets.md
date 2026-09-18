# The sheets

One Google spreadsheet holds one week, named `Cabin Act Sorting - S2W1`. All of them live
in one Drive folder, which is what **Link to Google Sheets** picks. A spreadsheet whose name
does not end in a session and week code is ignored, so notes and old copies can sit in the
same folder.

Each week's spreadsheet has four tabs.

## Board

The grid. Row 1 is the title, row 2 the day names, row 3 the day subtitles. Below that,
every cabin gets six rows and every day gets five columns, and every card block looks the
same:

```
   A          B             C                        D         E       F (hidden)
 ┌────────┬─────────────┬────────────────────────┬──────────┬───────┬──────────┐
 │        │ Monday                                                  │          │
 │        │ Coco's Day                                              │          │
 ├────────┼─────────────┼────────────────────────┼──────────┼───────┼──────────┤
 │ MANZI  │ Activity    │ Becoming a team <3     │ Van      │ ☐     │ 9f2a1c…  │
 │ M1     │ Description │ Do low ropes to work…  │ Risk     │ N     │          │
 │ Jana   │ Materials   │ rope, blindfolds       │ Armory   │ ☐     │          │
 │        │ Location    │ Low Ropes 1            │ Picnic   │ ☐     │          │
 │        │ Notes       │ Needs a facilitator    │ Food     │ ☐     │          │
 │        │ HEROES      │ Dylan, Vic             │          │       │          │
 └────────┴─────────────┴────────────────────────┴──────────┴───────┴──────────┘
```

- **Materials** and **HEROES** are comma separated.
- **Location** has a dropdown drawn from the Locations tab.
- **Risk** has a dropdown of `R`, `Y`, `G` and `N`, and colours itself.
- **Van**, **Armory**, **Picnic** and **Food** are checkboxes.
- The sixth column of each block holds the card's id and is hidden. It is what keeps a
  card's comments with it when the card is moved. Do not delete it.

Filling a card in on the sheet rather than in Brain Waves works fine: the next poll picks
it up, and a card with no id is given one.

## Roster

`Cabin | Counselor | Co-Counselor`, one row per cabin. This tab decides which cabins have
rows on the board and in what order: cabin names beginning M, P, O and C fall into Manzi,
Pine, Oak and Cedar, in that order, and are sorted by name within a village. The **Cabins**
button writes this tab.

## Locations

One location per row under a `Location` heading. This is the list the Location dropdown
offers, both on the sheet and in Brain Waves. Add to it freely; a new week copies the list
from the week it was made after.

## Support Requests

Derived, never edited. Brain Waves rewrites it whenever the board changes, and it lists,
for each weekday, every cabin act that asks anything of staff outside the cabin: which
HEROES, and whether it needs a van, the armory, a picnic or other food. This is the tab the
Puppet Master reads.

## The template

There is no template spreadsheet to copy and keep in step. The template is the code:
`brainwaves.workspace.write_template` writes those four tabs and then formats the Board, and
**Start New Week** calls it. To see one without making a week in Drive:

```
brainwaves template --csv /tmp/template
```

To put a blank week straight into a Drive folder:

```
brainwaves template --folder <drive folder id> --session 2 --week 1
```

A new week keeps the cabins and locations of the newest week already open, so a session
does not have to be typed in twice.
