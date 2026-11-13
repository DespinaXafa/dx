"""
ΒΗΜΑ 5 — Αξιολόγηση. Τυπώνει Hit@1/3/5, MRR και τα αποτελέσματα των 10 παραδειγμάτων Rules as Code.

    python scripts/evaluate.py [--no-embeddings] [--source sample|cache|hf|auto]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.data import load_procedures  # noqa: E402
from core.evaluation import eval_retrieval, eval_rules, load_queries  # noqa: E402
from core.search import ProcedureSearch  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--no-embeddings", action="store_true")
ap.add_argument("--source", default="auto")
a = ap.parse_args()

procs, src = load_procedures(a.source)
eng = ProcedureSearch(procs, use_embeddings=not a.no_embeddings)
print(f"Πηγή: {src} · {len(procs)} διαδικασίες · μέθοδος: {eng.mode}\n")

m, rows = eval_retrieval(eng, load_queries())
for r in rows:
    print(f"  [{r.rank or '-':>2}] {r.query[:45]:45s} → {r.top1[:55]}")
print("\nRETRIEVAL:", {k: round(v, 3) if isinstance(v, float) else v for k, v in m.items()})

acc, rr = eval_rules()
print(f"\nRULES AS CODE: ακρίβεια {acc:.0%} ({sum(r['pass'] for r in rr)}/{len(rr)})")
for r in rr:
    print(f"  {'PASS' if r['pass'] else 'FAIL'}  {r['σενάριο']:40s} αναμ.={r['αναμενόμενο']!s:5} αποτ.={r['αποτέλεσμα']!s:5} {r['κανόνες που απέτυχαν']}")
