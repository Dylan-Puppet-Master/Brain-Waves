# Design

## What is authoritative

Google Sheets. Brain Waves holds a copy of one week so that dragging a card is instant, but
every change is written through to the sheet, and the sheet is read again as soon as anyone
else touches it. Nothing exists only inside the program, which is the point: when Brain
Waves is not being maintained any more, the sheets are still there and still readable.

## How it fits together

```
Google Drive ──┬── comments ──▶ google/comments.py ──▶ comments.py ─┐
               │                                                    │
               └── week sheet ──▶ sheets/week.py ──────────────────▶ model.py
                                        ▲                            │
                                        │                            ▼
                                  sheets/style.py               store.py ──▶ app/
                                  sheets/support.py                  │
                                        ▲                            │
                                        └──────── writes ────────────┘
```

| Module | Does |
|---|---|
| `brainwaves/model.py` | Cabin, CabinAct, Day, Week, Comment, and the moves on a week |
| `brainwaves/sheets/` | The Board format: geometry, parse, render, formatting, the derived Support Requests tab |
| `brainwaves/google/` | Sign-in, Drive browsing, Drive comments |
| `brainwaves/comments.py` | Which card a Drive thread is about |
| `brainwaves/workspace.py` | Finding, opening and creating week sheets |
| `brainwaves/store.py` | One loaded week, every change to it, and the queue of writes |
| `brainwaves/app/` | The window |
| `brainwaves/update.py` | Checking GitHub and replacing the running file |

## Decisions worth knowing about

**A card has an id, and the sheet carries it.** Without one, a comment could only be about a
position, and the whole point of the program is that positions change. The id lives in a
hidden column of each card block, so it survives being read and written by anyone.

**Comments are Google's, not ours.** A tab of our own would have been simpler to write and
worse to use: no notifications, no sidebar, no author. The cost is that anchoring a new
thread to a cell uses an undocumented shape, so `CommentStore.create` falls back to an
unanchored comment if Drive refuses the anchor. The comment is never lost.

**Every card block is the same shape.** That is what lets the whole of one day's formatting
and data validation go in a single `updateCells` request. A week's styling is about 160
requests; with merged title cells and per-card validation it was about 2500.

**Writes are one card block at a time.** Two village leaders filling in different cabins
never overwrite each other, because neither writes a cell the other touched. Only changing
the roster or adding an unplaced column rewrites the whole board.

**Changes are queued, not awaited.** `BoardStore` applies a change to its own copy and
appends the write to `pending`; `flush` sends the queue in order from a background thread.
The board moves at the speed of the mouse, and the writes still arrive in the order they
were made.

**Reading often is made cheap rather than done less.** Asking Drive for a file's revision
costs a couple of hundred bytes; reading a board costs several hundred kilobytes. `poll`
asks the cheap question every couple of seconds and reads only when the answer has changed,
so other people's edits show up about as fast as they make them and the network stays quiet
in between. A write of our own moves the revision too, so `flush` takes the revision
afterwards, but only when nobody else wrote while we were editing; where somebody did, the
revision is left stale and the next poll reads the board properly.

Google can push notifications instead of being asked, which would be better still, but only
to a public HTTPS endpoint on a verified domain. That means running a server, and a server
is the thing this program is meant not to need.

**A timer never raises a dialog.** A failed poll writes one line in the status bar and is
tried again; only something a person asked for — opening a week, creating one, saving —
is worth interrupting them for. At two seconds, the alternative is a wall of dialogs the
moment the wifi dips.

**The window never talks to Google.** Everything goes through `app/sync.JobQueue`, one job
at a time, reporting back through signals. There is no other thread, no lock, and no place
where the window can be waiting on the network.
