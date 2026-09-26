from dataclasses import replace

from brainwaves.model import CabinAct
from brainwaves.stats import MEASURES, spread, spreads

HEROES, FOOD, VAN, ARMORY, MATERIALS = MEASURES


def test_heroes_and_materials_count_every_one_asked_for(week):
    assert spread(week, HEROES).totals == [2, 0, 0, 0, 0]
    assert spread(week, MATERIALS).totals == [2, 0, 0, 0, 0]


def test_a_flag_counts_the_acts_that_carry_it(week):
    week = week.place("M2", 3, CabinAct(title="Cookout", food=True, van=True))
    week = week.place("P1", 3, CabinAct(title="Bake off", food=True))
    assert spread(week, FOOD).totals == [0, 0, 0, 2, 0]
    assert spread(week, VAN).totals == [0, 0, 0, 1, 0]
    assert spread(week, ARMORY).total == 0


def test_acts_without_a_day_load_no_day_but_are_still_counted(week):
    card = week.card("P1", 5)
    week = week.place("P1", 5, replace(card, heroes=("Vic",), armory=True))
    assert spread(week, HEROES).totals == [2, 0, 0, 0, 0]
    assert spread(week, HEROES).unplaced == 1
    assert spread(week, ARMORY).unplaced == 1


def test_a_day_knows_which_acts_make_it_up(week):
    (part,) = spread(week, HEROES).days[0].parts
    assert (part.cabin, part.title, part.count, part.names) == (
        "M1",
        "Becoming a team",
        2,
        ("Dylan", "Vic"),
    )


def test_tied_days_are_all_named(week):
    week = week.place("M2", 3, CabinAct(title="Cookout", heroes=("Ana", "Bo")))
    heroes = spread(week, HEROES)
    assert heroes.busiest == (0, 3)
    assert heroes.quietest == (1, 2, 4)
    assert heroes.gap == 2
    assert heroes.even_share == 0.8


def test_an_empty_measure_has_no_busiest_day(week):
    assert spread(week, VAN).busiest == ()
    assert spread(week, VAN).quietest == ()


def test_every_measure_is_counted_in_order(week):
    assert [s.measure.key for s in spreads(week)] == [
        "heroes",
        "food",
        "van",
        "armory",
        "materials",
    ]


def test_a_count_reads_as_english():
    assert HEROES.say(1) == "1 HERO"
    assert HEROES.say(3) == "3 HEROes"
    assert FOOD.say(2.5) == "2.5 food acts"
