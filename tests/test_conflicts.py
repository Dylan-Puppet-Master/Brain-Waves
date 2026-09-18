from dataclasses import replace

import pytest

from brainwaves.conflicts import HERO, LOCATION, cards_in, find_conflicts
from brainwaves.model import CabinAct, Risk


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
