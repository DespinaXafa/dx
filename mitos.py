"""
Φόρτωση και κανονικοποίηση του dataset glossAPI/mitos (parquet, 4.340 διαδικασίες, 21 στήλες).

Οι προϋποθέσεις είναι λίστα αντικειμένων με τα πεδία:
    conditions_num_id            αύξων αριθμός μέσα στη διαδικασία
    conditions_name              το κείμενο της προϋπόθεσης
    conditions_type              κατηγορία (π.χ. «Ηλικιακές»)
    conditions_alternative       true = είναι εναλλακτική κάποιας άλλης
    conditions_alternative_of    ο αριθμός της προϋπόθεσης της οποίας είναι εναλλακτική

Κανόνας «και / ή»:
    - Προϋποθέσεις που συνδέονται με conditions_alternative_of ανήκουν στην ΙΔΙΑ ομάδα (ή).
      Η σύνδεση είναι μεταβατική (αλυσίδες 3→2→1 = μία ομάδα).
    - Διαφορετικές ομάδες πρέπει να ισχύουν ΟΛΕΣ (και).
Ασυνέπειες του dataset σημαίνονται (flags) και δεν «διορθώνονται» με εικασίες:
    - alt_unlinked : conditions_alternative=true χωρίς conditions_alternative_of (78 στο dataset).
                     Συνδέεται με την ΑΜΕΣΩΣ ΠΡΟΗΓΟΥΜΕΝΗ προϋπόθεση (συμπέρασμα, όχι πεδίο του ΜΙΤΟΣ)
                     και η ομάδα σημειώνεται, ώστε η εφαρμογή να το λέει ρητά.
    - of_without_alt: conditions_alternative=false αλλά υπάρχει conditions_alternative_of
                      (η σύνδεση ακολουθείται, αφού δηλώνεται ρητά)
    - missing_target: conditions_alternative_of δείχνει σε αριθμό που δεν υπάρχει
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PARQUET = ROOT / "data" / "mitos.parquet"


def _j(x, default):
    if x is None or (isinstance(x, float) and x != x) or x == "":
        return default
    try:
        return json.loads(x)
    except (TypeError, ValueError):
        return default


@dataclass
class Condition:
    num: int
    text: str
    ctype: str = ""
    alternative: bool = False
    alternative_of: int | None = None
    url: str = ""


@dataclass
class Group:
    members: list[int]             # conditions_num_id
    flags: list[str] = field(default_factory=list)

    @property
    def is_or(self) -> bool:
        return len(self.members) > 1


@dataclass
class Procedure:
    id: str
    title: str
    description: str
    provider: str
    url: str
    cost: str
    time: str
    conditions: list[Condition]
    groups: list[Group]
    steps: list[dict]
    legislation: list[dict]
    documents: str

    def search_text(self) -> str:
        """ΜΟΝΟ κείμενο του ΜΙΤΟΣ: τίτλος + περιγραφή (χωρίς δικές μας λέξεις-κλειδιά)."""
        return f"{self.title}. {self.description}".strip()

    def cond(self, num: int) -> Condition:
        return next(c for c in self.conditions if c.num == num)


# --------------------------------------------------------------------- και / ή

def build_groups(conds: list[Condition]) -> list[Group]:
    nums = [c.num for c in conds]
    parent = {n: n for n in nums}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    flags: dict[int, list[str]] = {n: [] for n in nums}
    for i, c in enumerate(conds):
        if c.alternative_of is not None:
            if c.alternative_of in parent:
                parent[find(c.num)] = find(c.alternative_of)
                if not c.alternative:
                    flags[c.num].append("of_without_alt")
            else:
                flags[c.num].append("missing_target")
        elif c.alternative:
            flags[c.num].append("alt_unlinked")
            if i > 0:                                  # συμπέρασμα: εναλλακτική της προηγούμενης
                parent[find(c.num)] = find(conds[i - 1].num)

    buckets: dict[int, list[int]] = {}
    for n in nums:                       # σειρά του ΜΙΤΟΣ
        buckets.setdefault(find(n), []).append(n)
    groups = []
    for members in buckets.values():
        g = Group(members=members)
        for m in members:
            g.flags.extend(flags[m])
        groups.append(g)
    return groups


def parse_conditions(raw) -> list[Condition]:
    out = []
    for i, c in enumerate(_j(raw, [])):
        of = c.get("conditions_alternative_of")
        out.append(Condition(
            num=int(c.get("conditions_num_id") or i + 1),
            text=(c.get("conditions_name") or "").strip(),
            ctype=c.get("conditions_type") or "",
            alternative=bool(c.get("conditions_alternative")),
            alternative_of=int(of) if of not in (None, "") else None,
            url=c.get("conditions_url") or "",
        ))
    return out


def parse_row(r) -> Procedure:
    org = _j(r["Θεσμικός φορέας"], {})
    provider = ((org.get("Θεσμικός φορέας") or {}).get("title") or {}).get("el", "")
    conds = parse_conditions(r["Προϋποθέσεις"])
    steps = [{
        "num": s.get("step_num_id"), "title": s.get("step_title") or "",
        "description": s.get("step_description") or "",
        "child": bool(s.get("step_child")), "previous": s.get("step_previous_child"),
        "exit": bool(s.get("step_exit")),
    } for s in _j(r["Βήματα"], [])]
    leg = [{
        "type": l.get("rule_type") or "", "number": l.get("rule_decision_number") or "",
        "year": l.get("rule_decision_year") or "", "article": l.get("rule_article") or "",
        "description": l.get("rule_description") or "", "url": l.get("rule_url") or "",
    } for l in _j(r["Νομοθεσία"], [])]
    nz = lambda v: "" if v is None or (isinstance(v, float) and v != v) else str(v)  # noqa: E731
    return Procedure(
        id=str(r["id"]), title=nz(r["title_el"]).strip(), description=nz(r["Περιγραφή"]).strip(),
        provider=provider, url=nz(r["source_url"]), cost=nz(r["Κόστος"]), time=nz(r["Εκτιμώμενος χρόνος"]),
        conditions=conds, groups=build_groups(conds), steps=steps, legislation=leg,
        documents=nz(r["Αριθμός δικαιολογητικών"]),
    )


def load(path: str | Path = PARQUET) -> list[Procedure]:
    df = pd.read_parquet(path)
    return [parse_row(r) for _, r in df.iterrows()]


def to_dict(p: Procedure) -> dict:
    d = asdict(p)
    d["groups"] = [{"members": g.members, "flags": g.flags} for g in p.groups]
    return d
