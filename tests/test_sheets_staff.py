"""Reading the two camp documents: who exists, what groups they are in, what they can do."""

from brainwaves.sheets.staff import (
    CATEGORY,
    PERSON,
    SKILL,
    StaffLists,
    parse_categories,
    parse_skills,
    parse_staff_names,
)

SKILLS_TAB = [
    ["group headings", "", "", "", "Ropes", "Ropes", "Crafts"],
    ["", "", "", "Canopy Tour", "Canopy Tour", "Low Ropes", "Bead working"],
    ["", "", "", "1st", "2nd", "", ""],
    ["Dylan", "3", "", "✓", "", "✓", "interested"],
    ["Vic", "2", "", "", "trainer", "", "✓"],
    ["Catana", "1", "", "past ex", "", "", "."],
    ["", "", "", "✓", "✓", "✓", "✓"],
]

CATEGORIES_TAB = [
    ["Counselor", "Director", "", "etc."],
    ["Dylan", "Lisa", "", "ignored"],
    ["Vic", "", "", ""],
    ["Catana", "", "", ""],
]


def test_names_are_read_in_sheet_order_without_the_headers():
    assert parse_staff_names(SKILLS_TAB) == ("Dylan", "Vic", "Catana")


def test_a_skill_is_its_heading_however_many_ranks_it_spans():
    skills = parse_skills(SKILLS_TAB)
    assert set(skills) == {"Canopy Tour", "Low Ropes", "Bead working"}


def test_a_skill_counts_the_people_who_can_actually_do_it():
    skills = parse_skills(SKILLS_TAB)
    assert skills["Canopy Tour"] == 2  # Dylan is checked off, Vic trains it, Catana used to
    assert skills["Low Ropes"] == 1
    assert skills["Bead working"] == 1  # "interested" and "." are not yet


def test_a_row_with_no_name_is_not_a_person():
    assert max(parse_skills(SKILLS_TAB).values()) <= 3


def test_categories_are_columns_of_names():
    categories = parse_categories(CATEGORIES_TAB)
    assert categories == {"Counselor": 3, "Director": 1}


def test_everything_selectable_is_offered_people_first():
    lists = StaffLists(names=("Dylan",), categories={"Counselor": 3}, skills={"Canopy Tour": 2})
    assert lists.options == ("Dylan", "Counselor", "Canopy Tour")


def test_a_chip_is_recognised_for_what_it_is():
    lists = StaffLists(names=("Dylan",), categories={"Counselor": 3}, skills={"Canopy Tour": 2})
    assert lists.kind_of("Dylan") == PERSON
    assert lists.kind_of("counselor") == CATEGORY
    assert lists.kind_of("Canopy Tour") == SKILL
    assert lists.kind_of("Someone's cousin") == PERSON


def test_how_many_people_a_chip_could_mean():
    lists = StaffLists(names=("Dylan",), categories={"Counselor": 3}, skills={"Canopy Tour": 2})
    assert lists.how_many("Dylan") == 1
    assert lists.how_many("Counselor") == 3
    assert lists.how_many("Canopy Tour") == 2
    assert lists.how_many("Someone's cousin") == 1


def test_empty_documents_read_as_empty_lists():
    assert parse_staff_names([]) == ()
    assert parse_skills([]) == {}
    assert parse_categories([]) == {}
