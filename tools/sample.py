"""A week of made-up cabin acts, used by the screenshot tool and by the docs."""

from brainwaves.model import Cabin, CabinAct, Day, Risk, Week, WeekId, sort_cabins
from brainwaves.sheets.staff import StaffLists

SAMPLE_LOCATIONS = (
    "Craft Shack 1",
    "Craft Shack 2",
    "Ceramics",
    "Field - Lake",
    "Field - Tiny",
    "Giant Swing",
    "Hot Rocks",
    "Lake - Outer 1",
    "Low Ropes 1",
    "Manzi",
    "Pine",
)

SAMPLE_STAFF = StaffLists(
    names=("Dylan", "Vic", "Catana", "Yolanne", "Donny", "Paul", "Tyson", "Brian", "Julian"),
    categories={"Counselor": 22, "Director": 3, "VL": 4, "EQ Staff": 3},
    skills={"Low Ropes": 7, "Canopy Tour": 14, "Giant Swing": 33, "Katana": 1},
)

CABINS = (
    ("M1", "Jana", ""),
    ("M2", "Elsa", "Ari"),
    ("M3", "Tala", ""),
    ("P1", "Robyn", ""),
    ("P2", "Cameron", ""),
    ("P3", "Liam", ""),
    ("O1", "Mavis", ""),
    ("O2", "Jayla", ""),
    ("C1", "Javi", ""),
    ("C2", "Davi", ""),
)

DAYS = (
    Day("Monday", "Coco's Day"),
    Day("Tuesday"),
    Day("Wednesday"),
    Day("Thursday", "Pizza Day"),
    Day("Friday"),
)


def sample_week() -> Week:
    """The week the documentation screenshot shows."""
    cards = {
        ("M1", 0): CabinAct(
            id="a1",
            title="Becoming a team",
            description="Low ropes to work on our teambuilding and trust",
            materials=("blindfolds", "rope"),
            location="Low Ropes 1",
            notes="Needs a low ropes facilitator",
            risk=Risk.YELLOW,
            picnic=True,
            heroes=("Dylan", "Low Ropes"),
        ),
        ("M1", 1): CabinAct(
            id="a2",
            title="We are a manzi garden",
            description="Make flower crowns and become flowers together",
            materials=("green wire", "fake flowers"),
            location="Craft Shack 1",
        ),
        ("M1", 3): CabinAct(
            id="a3",
            title="Collaborative crazy tie dye",
            description="Fill water balloons with dye and throw them at a big sheet",
            location="Craft Shack 1",
            risk=Risk.GREEN,
            food=True,
            heroes=("Catana",),
        ),
        ("M2", 0): CabinAct(
            id="b1",
            title="Slip and slide relay race",
            description="Relay tasks down the slip n slide",
            location="Manzi",
            risk=Risk.YELLOW,
            van=True,
            heroes=("Yolanne",),
        ),
        ("M2", 2): CabinAct(
            id="b2",
            title="Spa day at Hot Rocks",
            description="Face masks, nail polish and hot rocks",
            location="Hot Rocks",
            picnic=True,
        ),
        ("M3", 1): CabinAct(
            id="c1",
            title="Civil war of slime",
            description="A slime fight against another cabin",
            location="Field - Tiny",
            armory=True,
        ),
        ("M3", 2): CabinAct(
            id="c2",
            title="Hot rocks and hot chocolate",
            description="Sit in the hot rocks until the marshmallows run out",
            location="Hot Rocks",
            heroes=("Vic",),
        ),
        ("M3", 5): CabinAct(
            id="k1",
            title="Squishy scientists",
            description="Design and make our own squishies",
            location="Craft Shack 2",
        ),
        ("P1", 0): CabinAct(
            id="d1",
            title="Shelter for the trap door",
            description="Build a shelter behind Pine out of cardboard",
            materials=("twine", "duct tape", "cardboard x15"),
            location="Pine",
            heroes=("Dylan",),
        ),
        ("P2", 3): CabinAct(
            id="e1",
            title="Make a boat",
            description="Make a boat and float it down to the falls",
            location="Craft Shack 2",
            risk=Risk.RED,
            van=True,
            heroes=("Director", "Paul"),
        ),
        ("P3", 2): CabinAct(
            id="f1",
            title="Foam sword battle royale",
            description="Sword fighting clinic, but as a battle royale",
            location="Field - Tiny",
            risk=Risk.YELLOW,
            armory=True,
            heroes=("Tyson",),
        ),
        ("O1", 4): CabinAct(
            id="g1",
            title="Canoe the lake",
            description="Paddle out to the far dock and back",
            location="Lake - Outer 1",
            risk=Risk.YELLOW,
            heroes=("Mavis", "Brian"),
        ),
        ("O2", 1): CabinAct(
            id="h1",
            title="Giant swing sunrise",
            description="Everyone goes up at least once",
            location="Giant Swing",
            risk=Risk.RED,
            heroes=("Charlton",),
        ),
        ("C1", 0): CabinAct(
            id="i1",
            title="Flaming golf",
            description="Golf, but the balls are on fire",
            location="Field - Lake",
            risk=Risk.RED,
            armory=True,
            heroes=("Julian",),
        ),
        ("C2", 5): CabinAct(
            id="j1",
            title="Blacksmithing",
            description="Not yet given a day",
            location="Ceramics",
            risk=Risk.YELLOW,
        ),
    }
    cabins = sort_cabins(Cabin(*fields) for fields in CABINS)
    return Week(WeekId(2, 1), cabins, DAYS, cards)
