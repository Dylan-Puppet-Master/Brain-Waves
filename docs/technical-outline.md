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
| `brainwaves/conflicts.py` | Two cabins wanting one place or one HERO on one day |
| `brainwaves/workspace.py` | Finding, opening and creating week sheets |
| `brainwaves/store.py` | One loaded week, every change to it, and the queue of writes |
| `brainwaves/app/` | The window |
| `brainwaves/update.py` | Checking GitHub and replacing the running file |

## Decisions worth knowing about

**A card has an id, and the sheet carries it.** Without one, a comment could only be about a
position, and the whole point of the program is that positions change. The id lives in a
hidden column of each card block, so it survives being read and written by anyone.

**A card is written without touching what a comment points at.** Sheets pins a comment to a
cell and orphans it when that cell is rewritten, and Brain Waves rewrites cards constantly.
So a thread is anchored to the card's label cell — the one that reads `Activity`, which is
written once when the board is laid out and never again — and a card write goes only to the
value and flag columns beside it. That is also why laying the board out again clears only
what lies beyond it rather than wiping the tab.

**A clash is reported, never prevented.** `conflicts.py` is arithmetic on a `Week` and a
`StaffLists` and nothing else: no network, no window, no state. The Brain may well look at
two cabins on the lake and decide it is fine, so the program does not argue — it just makes
sure the choice is a choice rather than a surprise on the day.

**A HERO chip is not always a person.** It may be a category or a skill, meaning anyone who
fits, and the difference decides whether asking twice is a problem. Rather than mark the
kind on the sheet, which would make the cell harder for a person to read, the chip stays
plain text and is matched against the three lists when it is read: name, then category, then
skill, and a person if it is none of them. The counts come from the same read, which is what
lets "four cabins want a Director and camp has three" be a clash while "two cabins want a
Counselor" is not.

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

**The board is read, not asked about.** Drive can say when a file last changed, and that
answer is a couple of hundred bytes against the sixty kilobytes of reading a board. Brain
Waves used to use it, and it was wrong to: Google Sheets does not update a file's Drive
metadata promptly when someone edits a cell in the browser, so the check almost never
fired for the edits that mattered most. Worse, taking a fresh revision after writing could
adopt a revision that already contained somebody's unread edit, marking it seen and losing
it for good. Sixty kilobytes every three seconds is cheap enough; a change signal that
sometimes never arrives is not cheap at all.

What is still worth splitting is *what* gets read. The board is read every few seconds; the
roster, the locations and the comments every ten, because they change once a session.

**A read never undoes an unwritten change.** The week is read on the worker thread and
changed on the window's, so a card dragged while a read was in flight could be overwritten
by the older board that read came back with. The store keeps one lock, held only long
enough to swap one immutable `Week` for another and never across a network call, and a read
that finishes to find writes still queued is thrown away — what is on screen is newer than
what was read, so the next poll reads again.

**Google is allowed to wobble.** A small share of requests come back 429, 500, 502, 503 or
504, and the network drops out on its own account. None of that means the request was wrong,
so `google/retry.py` tries again after a longer wait each time. Only what can safely be
repeated goes through it: reading anything, writing cells, resolving a thread. Posting a
comment does not, because a second attempt would post it twice.

**A timer never raises a dialog.** A failed poll writes one line in the status bar and is
tried again; only something a person asked for — opening a week, creating one, saving —
is worth interrupting them for. At two seconds, the alternative is a wall of dialogs the
moment the wifi dips.

**The window never talks to Google.** Everything goes through `app/sync.JobQueue`, one job
at a time, reporting back through signals. There is no other thread, no lock, and no place
where the window can be waiting on the network.
