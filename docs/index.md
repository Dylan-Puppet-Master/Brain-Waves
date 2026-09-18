# Brain Waves

Brain Waves is how Camp Augusta plans cabin activities. Village leaders write each cabin's
ideas onto cards, the VL Brain drags those cards onto the days they will run, and everybody
argues about them in the comments. Google Sheets stays the source of truth, so nothing is
locked inside the program.

![The board](img/app.png)

## The week

1. Open Brain Waves. It reopens the session and week you had last.
2. Each village leader clicks an empty slot and fills in the cabin's activity: title,
   description, materials, location, notes, risk, what it needs, and which HEROES.
3. The VL Brain drags cards along a cabin's row until each day looks right. Anything that
   has not found a day sits in the **Extra** columns on the right.
4. The **Clashes** pane says whether two cabins have asked for the same place or the same
   HERO on the same day. Choose a row and the cards blink.
5. Anyone with a question clicks the card and writes a comment. The thread appears in the
   Google Sheets comment sidebar too, so people who prefer the sheet can answer there.
6. The **Support Requests** tab of the sheet rewrites itself as the board changes. That is
   the tab the Puppet Master reads to know what each day asks of non-counselor staff.

## Where things live

| Thing | Where |
|---|---|
| One week of cabin acts | A Google spreadsheet named `Cabin Act Sorting - S2W1` |
| Every week of a summer | One Google Drive folder, which you pick once |
| Staff names for the HERO chips | The Skills doc, the same one Puppet Strings reads |
| Your sign-in, folder and week | Your own computer, so the program opens where you left it |
| The code | This repository, one Python package |

Start with [Install and set up](install.md).
