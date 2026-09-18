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
