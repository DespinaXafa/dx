"""
Ερωτηματολόγιο «πληρώ τις προϋποθέσεις;» από τις προϋποθέσεις του ΜΙΤΟΣ.

- Κάθε ομάδα (core.mitos.build_groups) = μία ερώτηση.
    ομάδα 1 προϋπόθεσης  → «<κείμενο ΜΙΤΟΣ αυτούσιο>» — Ισχύει για εσάς; Ναι / Όχι / Δεν με αφορά
    ομάδα ≥2 (εναλλακτικές) → «Ισχύει τουλάχιστον ένα από τα παρακάτω;» με τα κείμενα αυτούσια
- Το κείμενο κάθε προϋπόθεσης εμφανίζεται ΑΥΤΟΥΣΙΟ (δεν αναδιατυπώνεται), ώστε η ερώτηση να λέει
  ακριβώς ό,τι η προϋπόθεση.
- «Δεν με αφορά»: πολλές προϋποθέσεις του ΜΙΤΟΣ ισχύουν μόνο σε ορισμένες περιπτώσεις
  (π.χ. «Για την ψηφιακή υποβολή…», ηλικιακές ομάδες). Δεν μετράει ως αποτυχία.
- Απόφαση: ΟΛΕΣ οι ομάδες (και) — μέσα σε ομάδα αρκεί ΜΙΑ (ή).
- Ομάδα με προϋπόθεση alt_unlinked (το ΜΙΤΟΣ τη λέει εναλλακτική χωρίς να λέει ποιας) έχει
  συνδεθεί με την προηγούμενη· η εφαρμογή το δείχνει ως σημείωση.
- Διαδικασία χωρίς προϋποθέσεις → status "none".
"""
from __future__ import annotations

from dataclasses import dataclass

from .mitos import Procedure

YES, NO, NA = "yes", "no", "na"


@dataclass
class Question:
    group: int
    kind: str                 # "single" | "any_of"
    prompt: str
    options: list[str]        # κείμενα προϋποθέσεων αυτούσια
    condition_nums: list[int]
    flags: list[str]


def build(p: Procedure) -> list[Question]:
    qs = []
    for gi, g in enumerate(p.groups):
        texts = [p.cond(n).text for n in g.members]
        if len(g.members) == 1:
            qs.append(Question(gi, "single", "Ισχύει για εσάς;", texts, g.members, g.flags))
        else:
            qs.append(Question(gi, "any_of", "Ισχύει τουλάχιστον ένα από τα παρακάτω;", texts, g.members, g.flags))
    return qs


@dataclass
class Verdict:
    status: str               # none | pending | eligible | not_eligible
    failed: list[int]         # δείκτες ομάδων που απέτυχαν
    unanswered: list[int]


def decide(p: Procedure, answers: dict[int, str]) -> Verdict:
    if not p.conditions:
        return Verdict("none", [], [])
    failed, unanswered = [], []
    for gi, _ in enumerate(p.groups):
        a = answers.get(gi)
        if a is None:
            unanswered.append(gi)
        elif a == NO:
            failed.append(gi)
    if failed:
        return Verdict("not_eligible", failed, unanswered)
    if unanswered:
        return Verdict("pending", [], unanswered)
    return Verdict("eligible", [], [])


def logic_string(p: Procedure) -> str:
    """π.χ. «(1 ή 2) και 3» — για αναφορές/αξιολόγηση."""
    parts = []
    for g in p.groups:
        s = " ή ".join(map(str, g.members))
        parts.append(f"({s})" if len(g.members) > 1 else s)
    return " και ".join(parts) if parts else "—"
