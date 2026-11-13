"""
Αυτόματο ερωτηματολόγιο «πληρώ τις προϋποθέσεις;» από τη λίστα προϋποθέσεων.

Λογική:  ΠΛΗΡΟΥΝΤΑΙ = AND(ομάδες),  ομάδα = OR(εναλλακτικές)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .schema import Procedure


@dataclass
class Question:
    idx: int
    kind: str            # "yesno" | "any_of"
    text: str
    options: list[str]


def to_question(statement: str) -> str:
    """Μετατροπή διατύπωσης προϋπόθεσης σε ερώτηση (κανόνες, χωρίς LLM)."""
    s = statement.strip().rstrip(".;:")
    if s.endswith(";") or s.endswith("?"):
        return s
    if re.match(r"^(Είστε|Έχετε|Δεν|Διαθέτετε|Υπάρχει|Ο αιτών|Η αιτούσα|Το|Η|Ο)\b", s):
        return s + ";"
    # απρόσωπες/ονοματικές διατυπώσεις, π.χ. «Ηλικία άνω των 18 ετών»
    return f"Ισχύει για εσάς: «{s}»;"


def build(proc: Procedure) -> list[Question]:
    qs = []
    for i, g in enumerate(proc.requirements):
        if len(g) == 1:
            qs.append(Question(i, "yesno", to_question(g[0]), ["Ναι", "Όχι"]))
        else:
            qs.append(Question(i, "any_of", "Ισχύει τουλάχιστον ένα από τα παρακάτω;", g))
    return qs


@dataclass
class Verdict:
    complete: bool
    eligible: bool | None
    failed: list[str]
    unanswered: list[int]


def decide(proc: Procedure, answers: dict[int, bool | None]) -> Verdict:
    """answers[i] = True (ισχύει / ισχύει κάποια εναλλακτική), False, ή None (αναπάντητο)."""
    failed, unanswered = [], []
    for i, g in enumerate(proc.requirements):
        a = answers.get(i)
        if a is None:
            unanswered.append(i)
        elif a is False:
            failed.append(g[0] if len(g) == 1 else "Καμία από: " + " / ".join(g))
    if failed:
        return Verdict(not unanswered, False, failed, unanswered)
    if unanswered:
        return Verdict(False, None, [], unanswered)
    return Verdict(True, True, [], [])
