# Using the board

One row per cabin, grouped by village. One column per weekday, then the **Unplaced**
columns for activities that have not been given a day.

## Cards

- **Click** a card to select it. Its comments appear in the panel on the right.
- **Double-click** a card to edit it.
- **Click an empty slot** to add a card there.
- **Drag** a card onto another slot in the same cabin's row. The two swap. Dropping onto an
  empty slot moves the card there.

A card cannot be dragged into another cabin's row. While a card is in the air, that cabin's
own row is tinted to show where it can go. That is deliberate: a cabin's activities belong
to that cabin.

Moving a card is instant. The board does not wait for Google — the card is where you put it
straight away, the write is sent behind it, and the line at the top right says when it has
landed.

## What a card shows

| On the card | Means |
|---|---|
| Bold title | The activity |
| Grey line under it | The description |
| Dark line | The location |
| `R` `Y` `G` `N` badge | Risk: red needs director sign-off, yellow is risk-managed, green needs a trained facilitator, none needs neither |
| Amber number | Open comments |
| Grey chips | Van, Armory, Picnic, Food, Level 2 on Ground, when the activity needs them |
| Teal chips | The HEROES asked for. A filled chip is a person by name; an outlined one is a category or a skill, meaning anyone who fits |

Hover a card to see everything, materials and notes included.

## Week stats

The **Week stats** tile in the top-left corner, above the cabins and beside Monday, opens
the week's statistics. It grows out of the corner and fills the board, the way a card does
when you open it. Its little columns are a real count: whichever measure you last looked
at, HEROes when Brain Waves starts, day by day. Switch to Materials and close the panel,
and the tile keeps showing materials, and the panel opens on them again next time.

Across the top is one tile per measure, each with its total for the week:

| Tile | Counts, per weekday |
|---|---|
| HEROes | Every HERO asked for, so a card asking for two counts two |
| Food | Acts with Food ticked |
| Van | Acts with Van needed ticked |
| Armory | Acts with Armory ticked |
| Materials | Every item in a card's materials list |

Click a tile, or press the left and right arrows or 1 to 5, to put that measure on the
chart. There is one column per weekday. The dashed **Even split** line shows where every
column would stand if the week's total were spread evenly, so a column well above it is
the day to move something off. Hover a column to see which cabins and acts make it up.
The sentence under the chart names the busiest and quietest days. Acts in Extra have no
day, so they add to no column; the sentence says how many are waiting there.

The statistics keep up as cards move, yours and everyone else's. Press **Esc**, **Close**,
or click outside the panel to go back to the board.

## The rest of the toolbar

| Control | Does |
|---|---|
| Session, Week | Which sheet is open. Changing either opens that week |
| Link to Google Sheets | Pick the folder the week sheets live in, in My Drive, in a shared drive, or in something shared with you |
| Cabins | Add, rename or remove cabins. Names starting M, P, O or C fall into Manzi, Pine, Oak and Cedar |
| Refresh | Read everything again now, rather than waiting for the next poll |
| Check for updates | Ask GitHub for a newer Brain Waves |

The line to the right of the buttons says how full the week is, or what Brain Waves is
doing at that moment.

## Starting a week

Set the session and week in the toolbar. If there is no sheet for them yet, the window says
so and offers to make one; press **Start New Week** and the sheet is created from the
template, with the cabins and locations of the week you had open. It refuses if that week
already exists, so pressing it twice cannot make two.

## Asking for a HERO

Press **+ HERO** in the card editor and type. Three kinds of thing can go in a chip, and
the list completes against all of them:

| Chip | Means | Where the list comes from |
|---|---|---|
| `Dylan` | That person | The names on the Skills doc |
| `Counselor` | Any one of the counselors | The column headings of the Staff Categories doc |
| `Canopy Tour` | Anyone checked off on it | The skill headings of the Skills doc |

A person's chip is filled in; a category or a skill is outlined, so you can see at a glance
which cards need a particular body and which need only a warm one. Hover a chip to see how
many people it could mean. Anything not on any of the three lists is taken as a person's
name, so a chip never has to wait for a document to catch up.

## Clashes

Every cabin act runs in the same hour, so two cabins on the same day cannot both be at Low
Ropes 1 and cannot both have Dylan. The **Clashes** pane, under the comments, lists every
one of those: the day, what has been asked for too often, and which cabins asked. Choose a
row and those cards are outlined in red, and the board scrolls to the first of them.

Asking for a category or a skill twice is not a clash — camp has twenty-two counselors, so
two cabins can each have one. It becomes a clash when more cabins want one than there are
people who fit: three cabins wanting a Director when camp has three is fine, four is not.
Brain Waves counts the people under each category heading, and the people with something
other than a blank in any of a skill's columns.

Nothing is prevented. Two cabins at the lake may be perfectly fine, and the Brain is the one
who knows; the pane only makes sure nobody finds out on the day. A row leaves the list as
soon as one of the cards is changed or moved.

Activities in the Extra columns are left out, because an activity with no day cannot clash
with anything. Locations that say nothing about where a cabin will be — `_Other` and
`Wandering` — are left out too.

## Knowing that something is happening

A thin bar sweeps under the toolbar while a change is on its way to Google, and the line at
the top right says what is being done. Opening or creating a week takes longer, so those
take over the window and name the step they are on: creating one writes four tabs and then
formats them, which is several seconds of work.

Polling says nothing, deliberately. It happens every couple of seconds, and an indicator
that blinks constantly stops meaning anything. If the network drops, the line at the top
right says so and Brain Waves keeps trying.

## Day subtitles

Click the grey line under a day's name and type. "Pizza Day" or "Coco's Day" next to
Thursday saves someone planning a picnic that day.

## Extra columns

The three columns to the right of Friday hold activities with no day yet. The **+** in the
last heading adds another column. They are part of the sheet like any other column, so they
survive being closed and reopened.

## Working at the same time as other people

Everyone sees everyone else's work within a few seconds, whether it was done in Brain Waves
or typed straight into Google Sheets. The board is read again every three seconds and
redrawn when it has changed; the cabins, the locations and the comments are read every ten,
because they change once a session rather than all afternoon.

Both rates can be changed; see [Install and set up](install.md).

Each change is written as its own small block of cells, so one person's edit never
overwrites another's, and a card you have just moved is never undone by a read that was
already in flight. If the network drops, the line at the top right says so and Brain Waves
keeps trying.

!!! note
    Brain Waves reads the board rather than asking Google whether it changed. Google Sheets
    does not update a file's Drive timestamp promptly when a cell is edited in the browser,
    so asking is unreliable — an earlier version did ask, and edits made in Google Sheets
    went unnoticed for minutes or were missed altogether. Reading a full board costs about
    sixty kilobytes, which is affordable every few seconds and is the only thing that
    always works.
