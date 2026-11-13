"""Αξιολόγηση: retrieval (Hit@k, MRR) και Rules as Code (ακρίβεια σε 10 παραδείγματα)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .rules.unemployment_certificate import TEST_CASES, is_eligible
from .schema import norm
from .search import ProcedureSearch

QUERIES = Path(__file__).resolve().parent.parent / "eval" / "queries.csv"


@dataclass
class QueryResult:
    query: str
    expected: str
    rank: int | None        # θέση της σωστής διαδικασίας (1 = πρώτη), None = εκτός top-k
    top1: str


def load_queries(path: Path = QUERIES) -> list[tuple[str, str]]:
    with open(path, encoding="utf-8") as f:
        return [(r["query"], r["expected_title_contains"]) for r in csv.DictReader(f)]


def eval_retrieval(engine: ProcedureSearch, queries: list[tuple[str, str]], k: int = 10):
    """Σωστό = ο τίτλος της διαδικασίας περιέχει (χωρίς τόνους) το expected_title_contains."""
    rows = []
    for q, exp in queries:
        hits = engine.search(q, k=k)
        rank = next((i + 1 for i, h in enumerate(hits) if norm(exp) in norm(h.proc.title)), None)
        rows.append(QueryResult(q, exp, rank, hits[0].proc.title if hits else "-"))
    n = len(rows) or 1
    metrics = {
        "Hit@1": sum(r.rank == 1 for r in rows) / n,
        "Hit@3": sum(r.rank is not None and r.rank <= 3 for r in rows) / n,
        "Hit@5": sum(r.rank is not None and r.rank <= 5 for r in rows) / n,
        "MRR": sum(1 / r.rank for r in rows if r.rank) / n,
        "N": len(rows),
    }
    return metrics, rows


def eval_rules():
    rows = []
    for name, citizen, expected in TEST_CASES:
        d = is_eligible(citizen)
        rows.append({"σενάριο": name, "αναμενόμενο": expected, "αποτέλεσμα": d.eligible,
                     "κανόνες που απέτυχαν": ", ".join(r.id for r in d.failed) or "—",
                     "pass": d.eligible == expected})
    acc = sum(r["pass"] for r in rows) / len(rows)
    return acc, rows
