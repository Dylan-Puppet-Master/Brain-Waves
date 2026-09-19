# The sheets

One Google spreadsheet holds one week, named `Cabin Act Sorting - S2W1`. All of them live
in one Drive folder, which is what **Link to Google Sheets** picks. That folder can be
anywhere you can reach: your own Drive, a shared drive your team has, or a folder somebody
has shared with you. A camp folder is usually not in anybody's own Drive. The code is what
matters, not the rest of the name: `S4W1 acts (draft)` and `Copy of Cabin Act Sorting -
S4W1` are both read as session 4, week 1. A spreadsheet whose name holds no session and
week code at all is ignored, so notes and old copies can sit in the same folder.

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

- **Materials** and **HEROES** are comma separated. A HERO may be a person's name, a
  category from the Staff Categories doc, or a skill from the Skills doc; it is written
  plainly either way, so the cell reads the same to a person as it always did.
- **Location** has a dropdown drawn from the Locations tab.
- **Risk** has a dropdown of `R`, `Y`, `G` and `N`, and colours itself.
- **Van**, **Armory**, **Picnic** and **Food** are checkboxes.
- The sixth column of each block holds the card's id and is hidden. It is what keeps a
  card's comments with it when the card is moved. Do not delete it.

Filling a card in on the sheet rather than in Brain Waves works fine: the next poll picks
it up, and a card with no id is given one.

Brain Waves writes only the value and flag columns of a card, never the label column. A
Google Sheets comment about a card is anchored to that label cell, and rewriting it would
tell Google the commented-on content had been deleted. See [Comments](comments.md).

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

## A sheet that has lost a tab

Opening a week whose Roster, Locations or Support Requests tab is gone rebuilds it instead
of refusing the sheet. Only the board cannot be worked out again, so it is read first and
checked: column A must name the cabins, and a card's rows must carry the labels Brain Waves
writes. If they do not, nothing is written and the message says which cell is wrong, because
a board laid out some other way would be read into the wrong cells.

If the board passes, the missing tabs are written from it - the cabins and who leads them
come from column A, the support requests from the cards, and the locations from the standard
list - and the Board is formatted again. A tab that is still there is left exactly as it is.
Cabins found out of village order are laid out again in it, since from then on the Roster's
order is what says which row belongs to which cabin.
