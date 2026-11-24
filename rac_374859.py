"""
RULES AS CODE: ΜΙΤΟΣ 374859 «Βεβαίωση ανεργίας για παροχή ιατροφαρμακευτικής περίθαλψης»
https://id.mitos.gov.gr/374859

Οι κανόνες γράφονται ΜΟΝΟ από τις 4 προϋποθέσεις της εγγραφής (πεδίο «Προϋποθέσεις»).
Δεν προστίθεται κανένας άλλος κανόνας (π.χ. υπηκοότητα, όριο 18 ετών).

Κείμενο προϋποθέσεων (αυτούσιο από το ΜΙΤΟΣ):
  [1] Οι άνεργοι νέοι ηλικίας μέχρι 29 ετών θα πρέπει να είναι εγγεγραμμένοι ως άνεργοι στο
      Μητρώο της Δ.ΥΠ.Α. για ένα τουλάχιστον δίμηνο.
  [2] Οι άνεργοι ηλικίας άνω των 29 έως 55 ετών, θα πρέπει να είναι εγγεγραμμένοι ως άνεργοι
      στο Μητρώο της Δ.ΥΠ.Α. για ένα συνεχές τουλάχιστον δωδεκάμηνο.
  [3] Οι άνεργοι ηλικίας άνω των 55 ετών, θα πρέπει να είναι εγγεγραμμένοι ως άνεργοι στο
      Μητρώο της Δ.ΥΠ.Α. επί ένα συνεχές δωδεκάμηνο.
  [4] Για την ψηφιακή υποβολή αίτησης για την έκδοση βεβαίωσης απαιτείται η χρήση προσωπικών
      κωδικών πρόσβασης στο Π.Σ. της ΔΥΠΑ είτε προσωπικών κωδικών taxisnet.

Παρατήρηση: στο ΜΙΤΟΣ οι [1]–[3] ΔΕΝ σημειώνονται ως εναλλακτικές (conditions_alternative=false),
άρα το γενικό ερωτηματολόγιο θα τις ζητούσε όλες μαζί («και»). Από το κείμενο όμως φαίνεται
ότι εφαρμόζεται ΜΟΝΟ μία, ανάλογα με την ηλικιακή ομάδα. Οι κανόνες εδώ το εκφράζουν σωστά.

Ερμηνείες (γραμμένες ρητά, ώστε να ελέγχονται):
  - Ηλικία = συμπληρωμένα έτη. «μέχρι 29» → age ≤ 29. «άνω των 29 έως 55» → 30 ≤ age ≤ 55.
    «άνω των 55» → age ≥ 56.
  - «δίμηνο» → τουλάχιστον 2 μήνες εγγραφής. «δωδεκάμηνο» → τουλάχιστον 12 μήνες.
  - «συνεχές» απαιτείται ΜΟΝΟ στα [2] και [3]· το [1] δεν το γράφει, άρα δεν απαιτείται.
  - [3] γράφει «επί ένα συνεχές δωδεκάμηνο» χωρίς «τουλάχιστον»· το ερμηνεύουμε ως ≥ 12 μήνες
    (όποιος έχει 14 συνεχείς μήνες έχει διανύσει και ένα συνεχές δωδεκάμηνο).
  - [4] ισχύει μόνο αν η αίτηση υποβάλλεται ψηφιακά.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

MITOS_ID = "374859"
MITOS_URL = "https://id.mitos.gov.gr/374859"


class Submission(str, Enum):
    DIGITAL = "digital"        # ψηφιακή υποβολή
    IN_PERSON = "in_person"    # μέσω ΚΕΠ / υπηρεσίας


@dataclass(frozen=True)
class Applicant:
    age: int                        # συμπληρωμένα έτη
    registered: bool                # εγγεγραμμένος ως άνεργος στο Μητρώο ΔΥΠΑ
    months_registered: int          # μήνες εγγραφής
    continuous: bool                # η εγγραφή είναι συνεχής (χωρίς διακοπή)
    submission: Submission
    has_dypa_codes: bool = False
    has_taxisnet: bool = False


@dataclass(frozen=True)
class Rule:
    id: str
    condition_num: int              # conditions_num_id στο ΜΙΤΟΣ
    applies: Callable[[Applicant], bool]
    check: Callable[[Applicant], bool]
    text: str


RULES: list[Rule] = [
    Rule("R1", 1, lambda a: a.age <= 29,
         lambda a: a.registered and a.months_registered >= 2,
         "Έως 29 ετών: εγγραφή στο Μητρώο ΔΥΠΑ για τουλάχιστον 2 μήνες"),
    Rule("R2", 2, lambda a: 30 <= a.age <= 55,
         lambda a: a.registered and a.continuous and a.months_registered >= 12,
         "30–55 ετών: συνεχής εγγραφή στο Μητρώο ΔΥΠΑ για τουλάχιστον 12 μήνες"),
    Rule("R3", 3, lambda a: a.age >= 56,
         lambda a: a.registered and a.continuous and a.months_registered >= 12,
         "Άνω των 55: συνεχής εγγραφή στο Μητρώο ΔΥΠΑ για 12 μήνες"),
    Rule("R4", 4, lambda a: a.submission == Submission.DIGITAL,
         lambda a: a.has_dypa_codes or a.has_taxisnet,
         "Ψηφιακή υποβολή: κωδικοί ΔΥΠΑ ή κωδικοί taxisnet"),
]


@dataclass(frozen=True)
class Decision:
    eligible: bool
    applied: tuple[str, ...]        # κανόνες που εφαρμόστηκαν
    failed: tuple[str, ...]         # κανόνες που απέτυχαν

    def explain(self) -> str:
        by_id = {r.id: r for r in RULES}
        if self.eligible:
            return "Πληρούνται οι προϋποθέσεις (" + ", ".join(self.applied) + ")."
        return "Δεν πληρούνται: " + "; ".join(f"{f} – {by_id[f].text}" for f in self.failed)


def evaluate(a: Applicant) -> Decision:
    applied = [r for r in RULES if r.applies(a)]
    failed = [r.id for r in applied if not r.check(a)]
    return Decision(not failed, tuple(r.id for r in applied), tuple(failed))


# Παραδείγματα ελέγχου ορίων (χρησιμοποιούνται από tests/ και από την εφαρμογή).
D, P = Submission.DIGITAL, Submission.IN_PERSON
EXAMPLES: list[tuple[str, Applicant, bool]] = [
    ("29 ετών, 2 μήνες εγγραφή (όριο ηλικίας και μηνών)", Applicant(29, True, 2, True, P), True),
    ("29 ετών, 1 μήνας εγγραφή", Applicant(29, True, 1, True, P), False),
    ("25 ετών, 2 μήνες ΜΗ συνεχόμενοι (το [1] δεν ζητά συνέχεια)", Applicant(25, True, 2, False, P), True),
    ("30 ετών, 12 συνεχείς μήνες (αλλαγή ηλικιακής ομάδας)", Applicant(30, True, 12, True, P), True),
    ("30 ετών, 11 συνεχείς μήνες", Applicant(30, True, 11, True, P), False),
    ("30 ετών, 12 μήνες με διακοπή", Applicant(30, True, 12, False, P), False),
    ("55 ετών, 12 συνεχείς μήνες (άνω όριο [2])", Applicant(55, True, 12, True, P), True),
    ("56 ετών, 12 συνεχείς μήνες (πρώτο έτος [3])", Applicant(56, True, 12, True, P), True),
    ("56 ετών, 11 συνεχείς μήνες", Applicant(56, True, 11, True, P), False),
    ("40 ετών, μη εγγεγραμμένος", Applicant(40, False, 0, False, P), False),
    ("25 ετών, 3 μήνες, ψηφιακά χωρίς κωδικούς", Applicant(25, True, 3, True, D), False),
    ("25 ετών, 3 μήνες, ψηφιακά με κωδικούς taxisnet", Applicant(25, True, 3, True, D, False, True), True),
]
