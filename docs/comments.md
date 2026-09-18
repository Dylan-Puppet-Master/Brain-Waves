# Comments

A comment in Brain Waves is a Google Drive comment on the week's spreadsheet. There is no
second discussion to keep in step: what is written in the panel appears in the Google
Sheets comment sidebar, what is written in the sidebar appears in the panel, both are
written by the person who wrote them, and Google sends its usual notifications.

## Writing one

Click a card, type in the box at the bottom of the panel, and press **Comment**. Reply in
the line inside a thread. **Resolve** closes a thread; **Show resolved** brings the closed
ones back into view.

## Which card a thread is about

Two ways, in this order.

1. **The tag.** A thread Brain Waves starts opens with a line naming the cabin, the day and
   the activity, ending in a marker like `[bw:9f2a1c4d]`. That is the card's id, so the
   thread stays with its card however far the card is dragged.
2. **The anchor.** A thread started in the Google Sheets sidebar has no tag, but Google
   records which cell it is anchored to. Brain Waves reads the anchor and gives the thread
   to whichever card covers that cell.

The card id also lives on the sheet, in a hidden column at the right-hand edge of each
card block. Deleting that column loses the thread's hold on its card; the thread itself is
safe, and will fall back to its anchor.

## When an activity is deleted

Deleting a card in Brain Waves answers each of its open threads to say the activity was
deleted, and closes them. The discussion is kept — Google shows resolved threads to anyone
who asks for them — but nobody is left reading an argument about an activity that is no
longer on the board.

An activity deleted on the sheet instead leaves its threads behind, because Brain Waves did
not do it and will not close someone else's discussion on a guess. Those threads are listed
in the comments panel when no card is selected, under **Comments with no activity**, where
they can be read and resolved.

## Why a comment does not say "original content deleted"

A Google Sheets comment is pinned to a cell, and Sheets marks it orphaned if that cell's
contents are rewritten. Brain Waves writes a card often — every edit, every drag — so it is
careful never to write the cell the comment is pinned to: a thread is anchored to the card's
label cell, in the narrow column that reads `Activity`, and card writes go only to the value
and flag columns beside it. Laying the board out again, for a new cabin or a new Extra
column, clears only what lies past the board rather than wiping the tab.

!!! note
    A thread anchored to a cell in the Sheets sidebar belongs to the card that is in that
    cell **now**. If the Brain in Brain Waves moves cards around after someone comments in
    the sidebar, that thread stays where it was written. Threads started in Brain Waves do
    not have that problem. It is worth telling people which of the two they are using.
