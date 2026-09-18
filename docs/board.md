# Using the board

One row per cabin, grouped by village. One column per weekday, then the **Unplaced**
columns for activities that have not been given a day.

## Cards

- **Click** a card to select it. Its comments appear in the panel on the right.
- **Double-click** a card to edit it.
- **Click an empty slot** to add a card there.
- **Drag** a card onto another slot in the same cabin's row. The two swap. Dropping onto an
  empty slot moves the card there.

A card cannot be dragged into another cabin's row: while a card is in the air, every slot
that will not take it fades. That is deliberate. A cabin's activities belong to that cabin.

## What a card shows

| On the card | Means |
|---|---|
| Bold title | The activity |
| Grey line under it | The description |
| Dark line | The location |
| `R` `Y` `G` `N` badge | Risk: red needs director sign-off, yellow is risk-managed, green needs a trained facilitator, none needs neither |
| Amber number | Open comments |
| Grey chips | Van, Armory, Picnic, Food, when the activity needs them |
| Teal chips | The HEROES asked for |

Hover a card to see everything, materials and notes included.

## The rest of the toolbar

| Control | Does |
|---|---|
| Session, Week | Which sheet is open. Changing either opens that week |
| Link to Google Sheets | Pick the Drive folder the week sheets live in |
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
