"""
RULES AS CODE — «Έκδοση βεβαίωσης ανεργίας» (ΔΥΠΑ)

Οι προϋποθέσεις της διαδικασίας (όπως καταγράφονται στο ΜΙΤΟΣ) μεταφράζονται σε
εκτελέσιμους κανόνες με τύπους δεδομένων. Κάθε κανόνας έχει:
  - κωδικό (R1..R5)
  - περιγραφή σε φυσική γλώσσα
  - νομική βάση (traceability προς τη νομοθεσία της διαδικασίας)
  - συνάρτηση ελέγχου

ΣΗΜΕΙΩΣΗ: Η ηλικία ≥ 18 είναι απλοποίηση για το εκπαιδευτικό παράδειγμα.
Πριν την παράδοση, επιβεβαιώστε τις προϋποθέσεις με την εγγραφή της διαδικασίας στο ΜΙΤΟΣ
και προσαρμόστε τους κανόνες/νομική βάση ανάλογα.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

PROCEDURE_TITLE_HINT = "βεβαιωση ανεργιασ"   # για εντοπισμό της εγγραφής στο dataset


class Citizenship(str, Enum):
    GR = "GR"      # Ελληνική
    EU = "EU"      # Κράτους-μέλους ΕΕ
    TCN = "TCN"    # Τρίτης χώρας


@dataclass(frozen=True)
class Citizen:
    age: int
    citizenship: Citizenship
    work_permit: bool          # άδεια διαμονής με πρόσβαση στην εργασία
    registered: bool           # εγγεγραμμένος στο Μητρώο Ανέργων ΔΥΠΑ με ενεργή κάρτα
    employed: bool             # μισθωτός ή ελεύθερος επαγγελματίας
    retired: bool              # συνταξιούχος γήρατος


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    legal_basis: str
    check: Callable[[Citizen], bool]


MIN_AGE = 18

RULES: list[Rule] = [
    Rule("R1", f"Ηλικία ≥ {MIN_AGE}", "απλοποίηση παραδείγματος",
         lambda c: c.age >= MIN_AGE),
    Rule("R2", "Έλληνας/ίδα ή πολίτης ΕΕ ή υπήκοος τρίτης χώρας με άδεια εργασίας", "Ν. 4921/2022",
         lambda c: c.citizenship in (Citizenship.GR, Citizenship.EU)
         or (c.citizenship == Citizenship.TCN and c.work_permit)),
    Rule("R3", "Εγγραφή στο Μητρώο Ανέργων ΔΥΠΑ (ενεργή κάρτα)", "Ν. 4921/2022",
         lambda c: c.registered),
    Rule("R4", "Δεν απασχολείται", "Ν. 1545/1985",
         lambda c: not c.employed),
    Rule("R5", "Δεν είναι συνταξιούχος γήρατος", "Ν. 1545/1985",
         lambda c: not c.retired),
]


@dataclass(frozen=True)
class Decision:
    eligible: bool
    failed: tuple[Rule, ...]

    def explain(self) -> str:
        if self.eligible:
            return "ΔΙΚΑΙΟΥΧΟΣ: πληρούνται όλοι οι κανόνες R1–R5."
        return "ΜΗ ΔΙΚΑΙΟΥΧΟΣ: " + "; ".join(f"{r.id} ({r.description})" for r in self.failed)


def is_eligible(c: Citizen) -> Decision:
    failed = tuple(r for r in RULES if not r.check(c))
    return Decision(eligible=not failed, failed=failed)


# 10 παραδείγματα με αναμενόμενη απάντηση (ground truth), που χρησιμοποιούνται
# στα unit tests (tests/test_rules.py) και στην καρτέλα αξιολόγησης της εφαρμογής.
G, E, T = Citizenship.GR, Citizenship.EU, Citizenship.TCN
TEST_CASES: list[tuple[str, Citizen, bool]] = [
    ("Άνεργος 34 ετών, Έλληνας, εγγεγραμμένος", Citizen(34, G, False, True, False, False), True),
    ("Ανήλικος 17 ετών", Citizen(17, G, False, True, False, False), False),
    ("Οριακή τιμή: ακριβώς 18 ετών", Citizen(18, G, False, True, False, False), True),
    ("Μη εγγεγραμμένος στη ΔΥΠΑ", Citizen(40, G, False, False, False, False), False),
    ("Εργάζεται ως μισθωτός", Citizen(29, G, False, True, True, False), False),
    ("Πολίτης ΕΕ, εγγεγραμμένος", Citizen(45, E, False, True, False, False), True),
    ("Τρίτης χώρας ΜΕ άδεια εργασίας", Citizen(33, T, True, True, False, False), True),
    ("Τρίτης χώρας ΧΩΡΙΣ άδεια εργασίας", Citizen(33, T, False, True, False, False), False),
    ("Συνταξιούχος γήρατος 67 ετών", Citizen(67, G, False, True, False, True), False),
    ("Πολίτης ΕΕ που εργάζεται", Citizen(25, E, False, True, True, False), False),
]
