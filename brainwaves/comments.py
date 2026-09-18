"""Which card a Drive thread is about.

Two ways, in order. A thread Brain Waves started carries a `[bw:<card id>]` tag, so it
follows its card wherever the card is moved to. A thread someone started in the Google
Sheets sidebar has no tag but does have an anchor, so it belongs to whichever card covers
the cell it is anchored to.
"""

import re

from brainwaves.google.comments import RawComment, anchored_cell, cell_anchor
from brainwaves.model import Comment, Reply, Week
from brainwaves.sheets import layout

TAG = re.compile(r"\[bw:([0-9a-zA-Z]+)\]")


def tag(card_id: str) -> str:
    """The marker that ties a comment to a card."""
    return f"[bw:{card_id}]"


def opening_line(cabin_label: str, column_label: str, title: str, card_id: str) -> str:
    """The first line of a thread Brain Waves starts, so the sheet's sidebar reads well."""
    subject = title or "untitled activity"
    return f"{cabin_label} - {column_label} - {subject} {tag(card_id)}"


def strip_tag(text: str) -> str:
    """The text as a person meant to write it.

    The opening line Brain Waves writes names the card for readers of the Google Sheets
    sidebar. In Brain Waves the panel already says which card this is, so that line goes.
    """
    kept = [line for line in text.splitlines() if not TAG.search(line)]
    return "\n".join(kept).strip() or TAG.sub("", text).strip()


def bind(threads, week: Week, tab_id: int) -> list[Comment]:
    """Match Drive threads to cards, dropping the ones that belong to no card."""
    by_slot = _cards_by_slot(week)
    bound = []
    for thread in threads:
        card_id = _tagged(thread) or _anchored(thread, by_slot, tab_id)
        if card_id:
            bound.append(_comment(thread, card_id))
    bound.sort(key=lambda c: c.latest, reverse=True)
    return bound


def anchor_for(week: Week, card_id: str, tab_id: int) -> str:
    """An anchor pinning a new thread to the card's title cell, or "" if it has moved away."""
    slot = week.locate(card_id)
    if slot is None:
        return ""
    cabin, column = slot
    index = next((i for i, c in enumerate(week.cabins) if c.name == cabin), None)
    if index is None:
        return ""
    row, left = layout.card_origin(index, column)
    return cell_anchor(tab_id, row, left)


def count_by_card(comments) -> dict[str, int]:
    """How many open threads each card has."""
    counts: dict[str, int] = {}
    for comment in comments:
        if not comment.resolved:
            counts[comment.card_id] = counts.get(comment.card_id, 0) + 1
    return counts


def orphaned(comments, week: Week) -> list[Comment]:
    """Open threads about cards that are no longer on the board.

    A card deleted in Brain Waves has its threads answered and closed. One deleted on the
    sheet, or in a week whose cabins have changed, leaves its threads behind; they are
    shown rather than left where nobody will ever find them.
    """
    live = {card.id for card in week.cards.values()}
    return sorted(
        (c for c in comments if c.card_id not in live and not c.resolved),
        key=lambda c: c.latest,
        reverse=True,
    )


def for_card(comments, card_id: str) -> list[Comment]:
    """One card's threads, open ones first."""
    mine = [c for c in comments if c.card_id == card_id]
    return sorted(mine, key=lambda c: (c.resolved, -c.latest.timestamp()))


def _cards_by_slot(week: Week) -> dict[tuple[int, int], str]:
    index_of = {cabin.name: index for index, cabin in enumerate(week.cabins)}
    return {
        (index_of[cabin], column): card.id
        for (cabin, column), card in week.cards.items()
        if cabin in index_of
    }


def _tagged(thread: RawComment) -> str:
    texts = [thread.text, *(reply.text for reply in thread.replies)]
    for text in texts:
        found = TAG.search(text)
        if found:
            return found.group(1)
    return ""


def _anchored(thread: RawComment, by_slot: dict[tuple[int, int], str], tab_id: int) -> str:
    cell = anchored_cell(thread.anchor)
    if cell is None or cell[0] != tab_id:
        return ""
    _, row, column = cell
    if row < layout.FIRST_CARD_ROW or column < layout.FIRST_CARD_COLUMN:
        return ""
    cabin_index = (row - layout.FIRST_CARD_ROW) // layout.CARD_ROWS
    card_column = (column - layout.FIRST_CARD_COLUMN) // layout.CARD_COLUMNS
    return by_slot.get((cabin_index, card_column), "")


def _comment(thread: RawComment, card_id: str) -> Comment:
    return Comment(
        id=thread.id,
        card_id=card_id,
        author=thread.author,
        created=thread.created,
        text=strip_tag(thread.text),
        resolved=thread.resolved,
        replies=tuple(
            Reply(r.id, r.author, r.created, strip_tag(r.text))
            for r in thread.replies
            if strip_tag(r.text)
        ),
    )
