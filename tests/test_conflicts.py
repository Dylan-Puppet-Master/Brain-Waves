from dataclasses import replace

import pytest

from brainwaves.conflicts import HERO, LOCATION, cards_in, find_conflicts
from brainwaves.model import CabinAct, Risk
from brainwaves.sheets.staff import StaffLists


def place(week, slots):
    for (cabin, column), card in slots.items():
        week = week.place(cabin, column, card)
    return week


def test_two_cabins_in_one_place_on_one_day_clash(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", title="Spa day", location="Hot Rocks"),
            ("P1", 1): CabinAct(id="two", title="Relaxing", location="Hot Rocks"),
        },
    )
    clash = find_conflicts(week)
    assert len(clash) == 1
    assert (clash[0].kind, clash[0].what, clash[0].day) == (LOCATION, "Hot Rocks", "Tuesday")
    assert set(clash[0].cabins) == {"M1", "P1"}
    assert set(clash[0].cards) == {"one", "two"}


def test_the_same_place_on_different_days_is_fine(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", location="Hot Rocks"),
            ("P1", 2): CabinAct(id="two", location="Hot Rocks"),
        },
    )
    assert find_conflicts(week) == []


def test_two_cabins_wanting_one_hero_clash(week):
    week = place(
        week,
        {
            ("M1", 2): CabinAct(id="one", heroes=("Dylan", "Vic")),
            ("O1", 2): CabinAct(id="two", heroes=("Dylan",)),
            ("C1", 2): CabinAct(id="three", heroes=("Vic",)),
        },
    )
    clashes = {c.what: c for c in find_conflicts(week)}
    assert set(clashes) == {"Dylan", "Vic"}
    assert clashes["Dylan"].kind == HERO
    assert set(clashes["Dylan"].cards) == {"one", "two"}
    assert set(clashes["Vic"].cards) == {"one", "three"}


def test_three_cabins_wanting_one_hero_is_one_clash(week):
    week = place(
        week,
        {
            ("M1", 0): CabinAct(id="one", heroes=("Dylan",)),
            ("P1", 0): CabinAct(id="two", heroes=("Dylan",)),
            ("O1", 0): CabinAct(id="three", heroes=("Dylan",)),
        },
    )
    clashes = find_conflicts(week)
    assert len(clashes) == 1
    assert len(clashes[0].cards) == 3


def test_spelling_does_not_hide_a_clash(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", location="Hot Rocks", heroes=("dylan",)),
            ("P1", 1): CabinAct(id="two", location="hot rocks ", heroes=("Dylan",)),
        },
    )
    assert {c.kind for c in find_conflicts(week)} == {LOCATION, HERO}


@pytest.mark.parametrize("vague", ["_Other", "Wandering", ""])
def test_a_location_that_says_nothing_does_not_clash(week, vague):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", title="x", location=vague),
            ("P1", 1): CabinAct(id="two", title="y", location=vague),
        },
    )
    assert find_conflicts(week) == []


def test_activities_with_no_day_yet_do_not_clash(week):
    week = place(
        week,
        {
            ("M1", 5): CabinAct(id="one", location="Hot Rocks", heroes=("Dylan",)),
            ("P1", 6): CabinAct(id="two", location="Hot Rocks", heroes=("Dylan",)),
        },
    )
    assert find_conflicts(week) == []


def test_one_cabin_alone_never_clashes_with_itself(week):
    week = place(week, {("M1", 1): CabinAct(id="one", location="Hot Rocks", heroes=("Dylan",))})
    assert find_conflicts(week) == []


def test_a_clash_reads_as_a_sentence(week):
    week = place(
        week,
        {
            ("M1", 3): CabinAct(id="one", location="Lake - Swing"),
            ("P1", 3): CabinAct(id="two", location="Lake - Swing"),
        },
    )
    assert find_conflicts(week)[0].summary == "Thursday: M1 and P1 both want Lake - Swing"


def test_every_clashing_card_is_listed(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", location="Hot Rocks", heroes=("Dylan",)),
            ("P1", 1): CabinAct(id="two", location="Hot Rocks"),
            ("O1", 1): CabinAct(id="three", heroes=("Dylan",)),
        },
    )
    assert cards_in(find_conflicts(week)) == {"one", "two", "three"}


def test_a_clean_week_has_nothing_to_report(week):
    assert find_conflicts(week) == []


def test_risk_and_other_fields_are_not_confused_for_clashes(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", risk=Risk.RED, van=True, notes="rope"),
            ("P1", 1): CabinAct(id="two", risk=Risk.RED, van=True, notes="rope"),
        },
    )
    assert find_conflicts(week) == []


def test_editing_a_card_out_of_the_way_clears_the_clash(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", location="Hot Rocks"),
            ("P1", 1): CabinAct(id="two", location="Hot Rocks"),
        },
    )
    assert find_conflicts(week)
    moved = week.place("P1", 1, replace(week.card("P1", 1), location="Manzi"))
    assert find_conflicts(moved) == []


CAMP = StaffLists(
    names=("Dylan", "Vic"),
    categories={"Counselor": 22, "Director": 3},
    skills={"Canopy Tour": 14, "Katana": 1},
)


def test_a_category_two_cabins_can_both_have_is_no_clash(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", heroes=("Counselor",)),
            ("P1", 1): CabinAct(id="two", heroes=("Counselor",)),
        },
    )
    assert find_conflicts(week, CAMP) == []


def test_a_skill_only_one_person_has_clashes(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", heroes=("Katana",)),
            ("P1", 1): CabinAct(id="two", heroes=("Katana",)),
        },
    )
    clash = find_conflicts(week, CAMP)[0]
    assert (clash.what, clash.available, clash.wanted) == ("Katana", 1, 2)


def test_asking_for_more_of_a_category_than_camp_has(week):
    week = place(
        week,
        {
            ("M1", 2): CabinAct(id="one", heroes=("Director",)),
            ("P1", 2): CabinAct(id="two", heroes=("Director",)),
            ("O1", 2): CabinAct(id="three", heroes=("Director",)),
            ("C1", 2): CabinAct(id="four", heroes=("Director",)),
        },
    )
    clash = find_conflicts(week, CAMP)[0]
    assert (clash.wanted, clash.available) == (4, 3)
    assert clash.summary == ("Wednesday: M1, P1, O1 and C1 want Director, and only 3 can")


def test_a_person_named_twice_still_clashes_when_camp_is_known(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", heroes=("Dylan",)),
            ("P1", 1): CabinAct(id="two", heroes=("Dylan",)),
        },
    )
    assert [c.what for c in find_conflicts(week, CAMP)] == ["Dylan"]


def test_a_name_nobody_recognises_is_treated_as_one_person(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", heroes=("Somebody's cousin",)),
            ("P1", 1): CabinAct(id="two", heroes=("Somebody's cousin",)),
        },
    )
    assert len(find_conflicts(week, CAMP)) == 1


def test_without_the_camp_documents_every_chip_counts_as_one_person(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", heroes=("Counselor",)),
            ("P1", 1): CabinAct(id="two", heroes=("Counselor",)),
        },
    )
    assert len(find_conflicts(week)) == 1  # erring towards saying something


def test_a_place_is_still_one_place_however_many_staff_there_are(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", location="Hot Rocks"),
            ("P1", 1): CabinAct(id="two", location="Hot Rocks"),
        },
    )
    assert find_conflicts(week, CAMP)[0].available == 1


def test_three_cabins_reads_as_three_cabins(week):
    week = place(
        week,
        {
            ("M1", 0): CabinAct(id="one", heroes=("Dylan",)),
            ("P1", 0): CabinAct(id="two", heroes=("Dylan",)),
            ("O1", 0): CabinAct(id="three", heroes=("Dylan",)),
        },
    )
    assert find_conflicts(week, CAMP)[0].summary == "Monday: M1, P1 and O1 all want Dylan"


def test_rest_hour_acts_do_not_clash_with_the_cabin_act_hour(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", title="RH Swim", location="Lake", heroes=("Dylan",)),
            ("P1", 1): CabinAct(id="two", title="Canoes", location="Lake", heroes=("Dylan",)),
        },
    )
    assert find_conflicts(week) == []


def test_rest_hour_acts_clash_with_each_other(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", title="RH Swim", location="Lake"),
            ("P1", 1): CabinAct(id="two", title="RH: Float", location="Lake"),
            ("O1", 1): CabinAct(id="three", title="Canoes", location="Lake"),
        },
    )
    (clash,) = find_conflicts(week)
    assert set(clash.cards) == {"one", "two"}
    assert clash.rest_hour
    assert clash.summary.startswith("Tuesday rest hour:")


def test_a_title_merely_starting_with_rh_is_not_rest_hour(week):
    week = place(
        week,
        {
            ("M1", 1): CabinAct(id="one", title="Rhythm", location="Lodge"),
            ("P1", 1): CabinAct(id="two", title="RHYTHM", location="Lodge"),
        },
    )
    assert len(find_conflicts(week)) == 1
