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


def test_a_poll_reads_the_board_and_leaves_the_other_tabs_alone(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.ROSTER_TAB, [["C9", "Newbie", ""]], "A99")
    assert store.poll() is False
    assert "C9" not in [c.name for c in store.week.cabins]


def test_reading_the_reference_tabs_picks_up_a_new_cabin(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.ROSTER_TAB, [["C9", "Newbie", ""]], "A99")
    assert store.reload_reference() is True
    assert "C9" in [c.name for c in store.week.cabins]


def test_reading_the_reference_tabs_keeps_the_board_it_already_has(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.LOCATIONS_TAB, [["Secret Pool"]], "A99")
    assert store.reload_reference() is False
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


def test_staff_names_come_from_the_skills_doc(tmp_path, week):
    store = store_for(tmp_path, week)
    store.load_staff()
    assert "Catana" in store.staff_names


def test_the_summary_counts_placed_and_unplaced(week):
    assert week_summary(week) == "2 of 25 days filled - 1 unplaced"


def test_a_poll_that_lands_on_an_unwritten_change_does_not_undo_it(tmp_path, week):
    """A card dragged while a poll was reading must survive the poll finishing."""
    store = store_for(tmp_path, week)
    read_board = store.workspace.read_board

    def read_then_drag(sheet, cabins=None):
        fresh = read_board(sheet, cabins)
        store.swap("M1", 0, 3)  # as if the user dragged a card mid-read
        return fresh

    store.workspace.read_board = read_then_drag
    assert store.poll() is False
    assert store.week.card("M1", 3).id == "aaa111"  # the drag stands
    store.workspace.read_board = read_board
    store.flush()
    store.poll()
    assert store.week.card("M1", 3).id == "aaa111"


def test_the_reference_read_also_leaves_an_unwritten_change_alone(tmp_path, week):
    store = store_for(tmp_path, week)
    store.workbook.write(week_sheet.ROSTER_TAB, [["C9", "Newbie", ""]], "A99")
    store.save_card("O1", 1, CabinAct(id="ddd444", title="Canoe"))
    assert store.reload_reference() is False
    assert store.week.card("O1", 1).title == "Canoe"
    store.flush()
    assert store.reload_reference() is True
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
    store.workbook.write_many = lambda tab, blocks: written.extend(blocks)
    store.save_card("M1", 0, None)
    store.flush()
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
