from brainwaves.model import CabinAct, Risk
from brainwaves.sheets import week as week_sheet
from brainwaves.store import BoardStore, week_summary
from tests.fakes import build


def store_for(tmp_path, week):
    workspace, sheet = build(tmp_path, week)
    return BoardStore(workspace, sheet)


def flushed(store):
    store.flush()
    return store


def test_a_saved_card_reaches_the_sheet(tmp_path, week):
    store = store_for(tmp_path, week)
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe", risk=Risk.YELLOW))
    store.flush()
    assert store.reload() is False
    assert store.week.card("O1", 1).title == "Canoe"


def test_clearing_a_slot_empties_it_on_the_sheet(tmp_path, week):
    store = store_for(tmp_path, week)
    store.save_card("M1", 0, None)
    store.flush()
    store.reload()
    assert store.week.card("M1", 0) is None


def test_a_swap_writes_both_blocks(tmp_path, week):
    store = store_for(tmp_path, week)
    store.swap("M1", 0, 3)
    store.flush()
    store.reload()
    assert store.week.card("M1", 0).title == "Tie dye"
    assert store.week.card("M1", 3).title == "Becoming a team"


def test_the_support_tab_lists_what_the_day_needs(tmp_path, week):
    store = store_for(tmp_path, week)
    store.save_card("M1", 0, store.week.card("M1", 0))
    store.flush()
    table = store.workbook.read(week_sheet.REQUESTS_TAB)
    rows = [row for row in table if row and row[0].startswith("M1")]
    assert rows and "Dylan, Vic" in rows[0]


def test_a_subtitle_is_written_to_its_own_cell(tmp_path, week):
    store = store_for(tmp_path, week)
    store.set_subtitle(3, "Pizza Day")
    store.flush()
    store.reload()
    assert store.week.days[3].subtitle == "Pizza Day"


def test_adding_an_overflow_column_widens_the_board(tmp_path, week):
    store = store_for(tmp_path, week)
    before = store.week.columns
    store.add_overflow_column()
    store.flush()
    store.reload()
    assert store.week.columns == before + 1


def test_a_comment_written_here_comes_back_bound_to_its_card(tmp_path, week):
    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Who is lifeguarding?")
    store.flush()
    assert [c.card_id for c in store.comments] == ["aaa111"]
    assert "Who is lifeguarding?" in store.comments[0].text


def test_a_comment_follows_its_card_across_a_swap(tmp_path, week):
    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Check the rope")
    store.flush()
    store.swap("M1", 0, 3)
    store.flush()
    store.reload()
    assert store.comments[0].card_id == "aaa111"
    assert store.week.card("M1", 3).id == "aaa111"


def test_replying_and_resolving(tmp_path, week):
    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Van needed?")
    store.flush()
    store.reply(store.comments[0].id, "Yes")
    store.flush()
    assert [r.text for r in store.comments[0].replies] == ["Yes"]
    store.resolve(store.comments[0].id)
    store.flush()
    assert store.comments[0].resolved


def test_a_poll_reports_no_change_when_there_is_none(tmp_path, week):
    store = store_for(tmp_path, week)
    assert store.poll() is False
    assert store.poll() is False


def test_a_poll_sees_an_edit_google_drive_would_not_have_reported(tmp_path, week):
    """The regression this replaced: Sheets does not bump its Drive metadata promptly.

    The fake Drive here never changes its revision, standing in for that. A poll must
    still notice the edit, which it only does by reading the board every time.
    """
    store = store_for(tmp_path, week)
    store.workspace.drive.frozen = True
    other = BoardStore(store.workspace, store.sheet)
    other.save_card("C1", 2, CabinAct(id="eee555", title="Blacksmithing"))
    other.flush()
    assert store.poll() is True
    assert store.week.card("C1", 2).title == "Blacksmithing"


def test_an_edit_made_while_we_were_editing_is_still_seen(tmp_path, week):
    """The other half of the regression: our own write must not mask someone else's."""
    store = store_for(tmp_path, week)
    other = BoardStore(store.workspace, store.sheet)
    other.save_card("C1", 2, CabinAct(id="eee555", title="Blacksmithing"))
    other.flush()
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe"))
    store.flush()
    assert store.poll() is True
    assert store.week.card("C1", 2).title == "Blacksmithing"
    assert store.week.card("O1", 1).title == "Canoe"


def test_our_own_write_is_not_reported_as_a_change(tmp_path, week):
    store = store_for(tmp_path, week)
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe"))
    store.flush()
    assert store.poll() is False


def test_a_poll_is_one_read(tmp_path, week):
    """The board, the roster and the locations come in one request, not one each."""
    store = store_for(tmp_path, week)
    before = store.workspace.reads
    store.poll()
    assert store.workspace.reads == before + 1


def test_a_poll_picks_up_a_new_cabin(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.ROSTER_TAB, [["C9", "Newbie", ""]], "A99")
    assert store.poll() is True
    assert "C9" in [c.name for c in store.week.cabins]


def test_a_poll_picks_up_a_new_location_and_keeps_the_board(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.LOCATIONS_TAB, [["Secret Pool"]], "A99")
    assert store.poll() is False
    assert "Secret Pool" in store.locations
    assert store.week.card("M1", 0).title == "Becoming a team"


def test_a_change_made_elsewhere_is_noticed(tmp_path, week):
    store = store_for(tmp_path, week)
    other = BoardStore(store.workspace, store.sheet)
    other.save_card("C1", 2, CabinAct(id="eee555", title="Blacksmithing"))
    other.flush()
    assert store.reload() is True
    assert store.week.card("C1", 2).title == "Blacksmithing"


def test_a_card_typed_onto_the_sheet_is_given_an_id_that_sticks(tmp_path, week):
    store = store_for(tmp_path, week)
    index = [c.name for c in store.week.cabins].index("O1")
    store.workbook.write(
        week_sheet.BOARD_TAB,
        [["Activity", "Canoe the lake", "Van", "FALSE", ""]],
        week_sheet.card_range(index, 2),
    )
    store.reload()
    given = store.week.card("O1", 2).id
    assert given
    store.flush()
    store.reload()
    assert store.week.card("O1", 2).id == given


def test_a_new_card_id_is_not_reported_as_a_change(tmp_path, week):
    store = store_for(tmp_path, week)
    index = [c.name for c in store.week.cabins].index("O1")
    store.workbook.write(
        week_sheet.BOARD_TAB,
        [["Activity", "Canoe the lake", "Van", "FALSE", ""]],
        week_sheet.card_range(index, 2),
    )
    assert store.reload() is True
    store.flush()
    assert store.reload() is False


def test_the_staff_lists_come_from_the_camp_documents(tmp_path, week):
    store = store_for(tmp_path, week)
    assert "Catana" in store.staff.names
    assert store.staff.categories["Counselor"] == 22
    assert store.staff.skills["Canopy Tour"] == 14
    assert "Counselor" in store.staff.options and "Canopy Tour" in store.staff.options


def test_the_summary_counts_placed_and_unplaced(week):
    assert week_summary(week) == "2 of 25 days filled - 1 unplaced"


def test_a_poll_that_lands_on_an_unwritten_change_does_not_undo_it(tmp_path, week):
    """A card dragged while a poll was reading must survive the poll finishing."""
    store = store_for(tmp_path, week)
    read = store.workspace.read

    def read_then_drag(workbook, week_id):
        fresh = read(workbook, week_id)
        store.swap("M1", 0, 3)  # as if the user dragged a card mid-read
        return fresh

    store.workspace.read = read_then_drag
    assert store.poll() is False
    assert store.week.card("M1", 3).id == "aaa111"  # the drag stands
    store.workspace.read = read
    store.flush()
    store.poll()
    assert store.week.card("M1", 3).id == "aaa111"


def test_a_new_cabin_waits_for_an_unwritten_change(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.ROSTER_TAB, [["C9", "Newbie", ""]], "A99")
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe"))
    assert store.poll() is False
    assert store.week.card("O1", 1).title == "Canoe"
    store.flush()
    assert store.poll() is True
    assert "C9" in [c.name for c in store.week.cabins]
    assert store.week.card("O1", 1).title == "Canoe"


def test_writing_a_card_leaves_the_cell_the_comment_is_anchored_to_alone(tmp_path, week):
    """A Google Sheets comment points at the card's label cell, which must never be rewritten.

    Rewriting it tells Google the commented-on content was deleted, which is what put
    "original content deleted" on threads people were still using.
    """
    from brainwaves.comments import anchor_for
    from brainwaves.google.comments import anchored_cell
    from brainwaves.sheets.source import a1_to_index

    store = store_for(tmp_path, week)
    _, row, column = anchored_cell(anchor_for(store.week, "aaa111", 0))
    written = []
    store.workbook.write_batch = lambda writes: written.extend(
        (cell, table) for tab, cell, table in writes if tab == week_sheet.BOARD_TAB
    )
    store.save_card("M1", 0, None)
    store.flush()
    assert written
    touched = {
        (a1_to_index(cell)[1] + offset)
        for cell, table in written
        for offset in range(max(len(line) for line in table))
    }
    assert column not in touched
    assert row  # the anchor is a real cell on the board


def test_deleting_a_card_closes_its_comments(tmp_path, week):
    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Who is lifeguarding?")
    store.flush()
    store.save_card("M1", 0, None)
    store.flush()
    assert [c.resolved for c in store.comments] == [True]
    assert "was deleted" in store.comments[0].replies[-1].text


def test_editing_a_card_leaves_its_comments_open(tmp_path, week):
    from dataclasses import replace

    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Who is lifeguarding?")
    store.flush()
    store.save_card("M1", 0, replace(store.week.card("M1", 0), title="Becoming a team again"))
    store.flush()
    assert [c.resolved for c in store.comments] == [False]


def test_a_swap_leaves_comments_open(tmp_path, week):
    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Who is lifeguarding?")
    store.flush()
    store.swap("M1", 0, 3)
    store.flush()
    assert [c.resolved for c in store.comments] == [False]


def test_a_thread_whose_card_went_elsewhere_is_findable(tmp_path, week):
    from brainwaves.comments import orphaned

    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Who is lifeguarding?")
    store.flush()
    index = [c.name for c in store.week.cabins].index("M1")
    store.workbook.write(
        week_sheet.BOARD_TAB,
        [["", "", "", "", ""]] * 6,
        week_sheet.card_range(index, 0),
    )
    store.poll()
    assert store.week.card("M1", 0) is None
    assert [c.card_id for c in orphaned(store.comments, store.week)] == ["aaa111"]


def test_rewriting_the_board_does_not_wipe_the_tab(tmp_path, week):
    cleared = []
    store = store_for(tmp_path, week)
    store.workbook.clear = lambda tab: cleared.append(tab)
    store.add_overflow_column()
    store.flush()
    assert week_sheet.BOARD_TAB not in cleared
    store.reload()
    assert store.week.card("M1", 0).title == "Becoming a team"


def test_a_poll_keeps_a_cabin_added_since_the_last_full_read(tmp_path, week):
    """A poll reads the board alone, so it must be told the cabins as they are now.

    Taking them from the sheet last read instead dropped a cabin added since, and reported
    the drop as a change.
    """
    from brainwaves.model import Cabin

    store = store_for(tmp_path, week)
    store.set_cabins([*store.week.cabins, Cabin("C9", "Tester")])
    store.flush()
    assert store.poll() is False
    assert "C9" in [c.name for c in store.week.cabins]


def writes_to(store):
    """Every call that writes cells, as the list of tabs each one touched."""
    calls = []
    write_batch = store.workbook.write_batch

    def counted(writes):
        calls.append([tab for tab, _, _ in writes])
        write_batch(writes)

    store.workbook.write_batch = counted
    return calls


def test_several_edits_waiting_together_go_in_one_request(tmp_path, week):
    store = store_for(tmp_path, week)
    calls = writes_to(store)
    store.swap("M1", 0, 3)
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe"))
    store.set_subtitle(2, "Pizza Day")
    store.flush()
    assert len(calls) == 1
    store.reload()
    assert store.week.card("M1", 3).id == "aaa111"
    assert store.week.card("O1", 1).title == "Canoe"
    assert store.week.days[2].subtitle == "Pizza Day"


def test_an_edit_that_changes_no_request_leaves_the_support_tab_alone(tmp_path, week):
    from dataclasses import replace

    store = store_for(tmp_path, week)
    calls = writes_to(store)
    applied = len(store.workbook.applied)
    card = store.week.card("M1", 0)
    store.save_card("M1", 0, replace(card, description="Something else entirely"))
    store.flush()
    assert calls == [[week_sheet.BOARD_TAB, week_sheet.BOARD_TAB]]
    assert len(store.workbook.applied) == applied  # and nothing is formatted


def test_the_support_tab_goes_in_the_same_request_as_the_card(tmp_path, week):
    store = store_for(tmp_path, week)
    calls = writes_to(store)
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe", van=True))
    store.flush()
    assert len(calls) == 1 and week_sheet.REQUESTS_TAB in calls[0]
    rows = [
        row
        for row in store.workbook.read(week_sheet.REQUESTS_TAB)
        if row and row[0].startswith("O1")
    ]
    assert rows and "Canoe" in rows[0]


def test_a_shorter_support_tab_leaves_nothing_behind(tmp_path, week):
    store = store_for(tmp_path, week)
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe", van=True))
    store.flush()
    store.save_card("O1", 1, None)
    store.flush()
    table = store.workbook.read(week_sheet.REQUESTS_TAB)
    assert not any("Canoe" in row for row in table)


def test_the_support_tab_is_reformatted_only_when_its_days_move(tmp_path, week):
    store = store_for(tmp_path, week)
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe", van=True))
    store.flush()
    applied = len(store.workbook.applied)
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe", van=True, food=True))
    store.flush()
    assert len(store.workbook.applied) == applied  # a tick changed; no heading moved
    store.save_card("C1", 0, CabinAct(id="eee555", title="Hike", van=True))
    store.flush()
    assert len(store.workbook.applied) > applied  # Tuesday onwards moved down a row


def test_a_new_subtitle_reaches_the_support_tab(tmp_path, week):
    store = store_for(tmp_path, week)
    store.set_subtitle(0, "Coco's Day")
    store.flush()
    table = store.workbook.read(week_sheet.REQUESTS_TAB)
    assert ["Monday", "Coco's Day"] in [row[:2] for row in table]


def test_a_support_tab_somebody_else_wrote_is_written_over(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.REQUESTS_TAB, [["stale"]], "A40")
    store.poll()
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe"))
    store.flush()
    assert not any("stale" in row for row in store.workbook.read(week_sheet.REQUESTS_TAB))


def test_a_failed_write_forgets_what_the_support_tab_holds(tmp_path, week):
    import pytest

    store = store_for(tmp_path, week)

    def refuse(writes):
        raise OSError("offline")

    store.workbook.write_batch = refuse
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe", van=True))
    with pytest.raises(OSError):
        store.flush()
    del store.workbook.write_batch
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe", van=True))
    store.flush()
    rows = [
        row
        for row in store.workbook.read(week_sheet.REQUESTS_TAB)
        if row and row[0].startswith("O1")
    ]
    assert rows


def test_closing_a_thread_is_one_call_per_thread(tmp_path, week):
    store = store_for(tmp_path, week)
    store.add_comment("aaa111", "Who is lifeguarding?")
    store.flush()
    replies = []
    store.workspace.comments.reply = lambda *args: replies.append(args)
    store.save_card("M1", 0, None)
    store.flush()
    assert replies == []
    assert store.comments[0].resolved


def test_a_week_deleted_in_drive_stops_syncing(tmp_path, week):
    """Sheets goes on writing to a spreadsheet in the trash; nothing here may."""
    store = store_for(tmp_path, week)
    store.workspace.drive.trashed = True
    store.reload_comments()
    assert store.gone
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe"))
    store.flush()
    assert not store.busy
    assert "Canoe" not in (tmp_path / "Board.csv").read_text()
