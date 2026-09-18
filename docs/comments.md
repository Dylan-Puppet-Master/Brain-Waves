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

!!! note
    A thread anchored to a cell in the Sheets sidebar belongs to the card that is in that
    cell **now**. If the Brain in Brain Waves moves cards around after someone comments in
    the sidebar, that thread stays where it was written. Threads started in Brain Waves do
    not have that problem. It is worth telling people which of the two they are using.
