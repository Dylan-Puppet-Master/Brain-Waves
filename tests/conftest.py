import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from brainwaves.model import Cabin, CabinAct, Risk, Week, WeekId, sort_cabins

WEEK_ID = WeekId(2, 1)


@pytest.fixture
def cabins():
    return sort_cabins(
        [
            Cabin("M1", "Jana"),
            Cabin("M2", "Elsa", "Ari"),
            Cabin("P1", "Robyn"),
            Cabin("O1", "Mavis"),
            Cabin("C1", "Javi"),
        ]
    )


@pytest.fixture
def week(cabins):
    cards = {
        ("M1", 0): CabinAct(
            id="aaa111",
            title="Becoming a team",
            description="Low ropes to work on teamwork",
            materials=("blindfolds", "rope"),
            location="Low Ropes 1",
            notes="Low ropes facilitator",
            risk=Risk.YELLOW,
            van=False,
            armory=False,
            picnic=True,
            food=False,
            level_two=True,
            heroes=("Dylan", "Vic"),
        ),
        ("M1", 3): CabinAct(id="bbb222", title="Tie dye", location="Craft Shack 1"),
        ("P1", 5): CabinAct(id="ccc333", title="Pirate ship battle", risk=Risk.NONE),
    }
    return Week(WEEK_ID, cabins, cards=cards)
