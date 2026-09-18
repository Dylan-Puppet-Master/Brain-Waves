from datetime import datetime

from brainwaves.comments import (
    anchor_for,
    bind,
    count_by_card,
    for_card,
    opening_line,
    strip_tag,
    tag,
)
from brainwaves.google.comments import RawComment, RawReply, anchored_cell, cell_anchor
from brainwaves.sheets import layout

NOW = datetime(2026, 6, 15, 9, 0).astimezone()
BOARD = 0


def thread(text, anchor="", replies=(), resolved=False, ident="t1"):
    return RawComment(ident, "Kestrel", NOW, text, resolved, anchor, tuple(replies))


def test_a_tagged_thread_finds_its_card_wherever_the_card_is(week):
    moved = week.swap("M1", 0, 4)
    bound = bind([thread(f"Needs a lifeguard {tag('aaa111')}")], moved, BOARD)
    assert bound[0].card_id == "aaa111"
    assert bound[0].text == "Needs a lifeguard"


def test_an_anchored_thread_finds_the_card_in_that_cell(week):
    index = [c.name for c in week.cabins].index("M1")
    row, left = layout.card_origin(index, 0)
    bound = bind([thread("Which low ropes?", cell_anchor(BOARD, row, left))], week, BOARD)
    assert bound[0].card_id == "aaa111"


def test_a_thread_about_nothing_is_dropped(week):
    assert bind([thread("Unrelated note")], week, BOARD) == []


def test_a_thread_anchored_to_another_tab_is_dropped(week):
    index = [c.name for c in week.cabins].index("M1")
    row, left = layout.card_origin(index, 0)
    assert bind([thread("Elsewhere", cell_anchor(7, row, left))], week, BOARD) == []


def test_replies_come_through_in_order(week):
    replies = [RawReply("r1", "Dylan", NOW, "On it")]
    bound = bind([thread(f"Van? {tag('aaa111')}", replies=replies)], week, BOARD)
    assert [r.text for r in bound[0].replies] == ["On it"]


def test_only_open_threads_are_counted(week):
    threads = [
        thread(f"Open {tag('aaa111')}", ident="t1"),
        thread(f"Closed {tag('aaa111')}", resolved=True, ident="t2"),
    ]
    bound = bind(threads, week, BOARD)
    assert count_by_card(bound) == {"aaa111": 1}
    assert [c.resolved for c in for_card(bound, "aaa111")] == [False, True]


def test_an_anchor_round_trips():
    assert anchored_cell(cell_anchor(3, 10, 4)) == (3, 10, 4)
    assert anchored_cell("not json") is None
    assert anchored_cell("") is None


def test_anchor_for_a_card_points_at_its_title_cell(week):
    index = [c.name for c in week.cabins].index("P1")
    assert anchored_cell(anchor_for(week, "ccc333", BOARD)) == (
        BOARD,
        *layout.card_origin(index, 5),
    )


def test_anchor_for_a_card_that_has_gone_is_empty(week):
    assert anchor_for(week, "missing", BOARD) == ""


def test_the_opening_line_names_the_card():
    line = opening_line("M1 - Jana", "Thursday - Pizza Day", "Tie dye", "bbb222")
    assert line.startswith("M1 - Jana - Thursday - Pizza Day - Tie dye")
    assert strip_tag(line).endswith("Tie dye")
