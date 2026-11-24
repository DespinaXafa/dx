"""Rules as Code 374859: παραδείγματα ορίων + έλεγχος ότι κάθε κανόνας αντιστοιχεί σε προϋπόθεση του ΜΙΤΟΣ."""
import pytest

from core.mitos import load
from core.rules.rac_374859 import EXAMPLES, MITOS_ID, RULES, evaluate


@pytest.mark.parametrize("name,applicant,expected", EXAMPLES, ids=[e[0] for e in EXAMPLES])
def test_examples(name, applicant, expected):
    assert evaluate(applicant).eligible is expected


def test_every_rule_maps_to_a_real_condition_and_no_extra_rules():
    proc = next(p for p in load() if p.id == MITOS_ID)
    nums = {c.num for c in proc.conditions}
    assert {r.condition_num for r in RULES} == nums      # ούτε λιγότεροι ούτε περισσότεροι


def test_exactly_one_age_rule_applies_for_any_age():
    from core.rules.rac_374859 import Applicant, Submission
    for age in range(15, 90):
        a = Applicant(age, True, 12, True, Submission.IN_PERSON)
        assert sum(r.applies(a) for r in RULES if r.condition_num in (1, 2, 3)) == 1
