"""ΒΗΜΑ 4 — 10 παραδείγματα ελέγχου ορθότητας των κανόνων.   pytest -v"""
import pytest

from core.rules.unemployment_certificate import TEST_CASES, Citizen, Citizenship, is_eligible


@pytest.mark.parametrize("name,citizen,expected", TEST_CASES, ids=[t[0] for t in TEST_CASES])
def test_ten_examples(name, citizen, expected):
    assert is_eligible(citizen).eligible is expected


def test_explanation_names_failed_rule():
    d = is_eligible(Citizen(17, Citizenship.GR, False, True, True, False))
    assert [r.id for r in d.failed] == ["R1", "R4"]
    assert "R1" in d.explain() and "R4" in d.explain()
