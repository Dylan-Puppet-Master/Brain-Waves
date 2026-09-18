import pytest

from brainwaves.model import Cabin, CabinAct, Risk, Village, WeekId


def test_village_from_cabin_name():
    assert Village.of("M3") is Village.MANZI
    assert Village.of("c2") is Village.CEDAR
    assert Village.of("X9") is None


def test_cabin_label_uses_both_counselors():
    assert Cabin("M2", "Elsa", "Ari").label == "M2 - Elsa & Ari"
    assert Cabin("M2", "Elsa").label == "M2 - Elsa"
    assert Cabin("M2").label == "M2"


@pytest.mark.parametrize(
    ("text", "risk"),
    [("R", Risk.RED), ("y", Risk.YELLOW), ("R/G", Risk.RED), ("", Risk.NONE), ("?", Risk.NONE)],
)
def test_risk_parses_what_the_sheet_holds(text, risk):
    assert Risk.parse(text) is risk


def test_blank_card_is_blank_whatever_its_flags_say():
    assert CabinAct(van=True, risk=Risk.RED).is_blank
    assert not CabinAct(title="Tie dye").is_blank


def test_week_id_round_trips_through_a_title():
    week_id = WeekId(2, 1)
    assert str(week_id) == "S2W1"
    assert WeekId.parse(week_id.title) == week_id
    assert WeekId.parse("Some other sheet") is None


def test_swap_exchanges_two_slots(week):
    swapped = week.swap("M1", 0, 3)
    assert swapped.card("M1", 0).title == "Tie dye"
    assert swapped.card("M1", 3).title == "Becoming a team"


def test_swap_into_an_empty_slot_moves_the_card(week):
    moved = week.swap("M1", 0, 1)
    assert moved.card("M1", 0) is None
    assert moved.card("M1", 1).title == "Becoming a team"


def test_place_removes_a_blank_card(week):
    assert week.place("M1", 0, None).card("M1", 0) is None


def test_locate_finds_a_card_by_id(week):
    assert week.locate("ccc333") == ("P1", 5)
    assert week.locate("nope") is None
