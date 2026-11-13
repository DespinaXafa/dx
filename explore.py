"""
ΒΗΜΑ 1 — Εξερεύνηση του dataset glossAPI/mitos.

    python scripts/explore.py            # πραγματικό dataset (χρειάζεται internet)
    python scripts/explore.py --sample   # τοπικό δείγμα

Τυπώνει: στήλες & τύπους, ένα ωμό παράδειγμα, ποια στήλη αντιστοιχίστηκε σε ποιο πεδίο,
και στατιστικά (προϋποθέσεις/εναλλακτικές/βήματα ανά διαδικασία). Γράφει data/explore_report.md.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd  # noqa: E402

from core.data import HF_DATASET, ROOT, _from_records, save_cache  # noqa: E402
from core.schema import load_override  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--sample", action="store_true")
ap.add_argument("--split", default="train")
args = ap.parse_args()

if args.sample:
    records = json.loads((ROOT / "data" / "sample_procedures.json").read_text(encoding="utf-8"))
else:
    from datasets import load_dataset
    ds = load_dataset(HF_DATASET, split=args.split)
    print("FEATURES:", ds.features)
    records = ds.to_list()

print(f"\nΕγγραφές: {len(records)}")
print("Στήλες:", list(records[0].keys()))
print("\nΩΜΟ ΠΑΡΑΔΕΙΓΜΑ (πρώτοι 400 χαρακτήρες ανά πεδίο):")
for k, v in records[0].items():
    print(f"  {k}: {str(v)[:400]!r}")

procs, cols = _from_records(records, load_override(ROOT / "schema_override.json"))
print("\nΑΝΤΙΣΤΟΙΧΙΣΗ ΣΤΗΛΩΝ (αν κάτι είναι λάθος → schema_override.json):")
for k, v in cols.items():
    print(f"  {k:13s} ← {v}")

df = pd.DataFrame({
    "title": [p.title for p in procs],
    "n_req": [len(p.requirements) for p in procs],
    "has_alt": [any(len(g) > 1 for g in p.requirements) for p in procs],
    "n_steps": [len(p.steps) for p in procs],
    "n_laws": [len(p.legislation) for p in procs],
    "provider": [p.provider for p in procs],
})
stats = {
    "διαδικασίες": len(df),
    "με προϋποθέσεις (%)": round((df.n_req > 0).mean() * 100, 1),
    "μ.ό. προϋποθέσεων": round(df.n_req.mean(), 2),
    "με εναλλακτικές (%)": round(df.has_alt.mean() * 100, 1),
    "με βήματα (%)": round((df.n_steps > 0).mean() * 100, 1),
    "μ.ό. βημάτων": round(df.n_steps.mean(), 2),
    "με νομοθεσία (%)": round((df.n_laws > 0).mean() * 100, 1),
    "φορείς": df.provider.nunique(),
}
print("\nΣΤΑΤΙΣΤΙΚΑ:")
for k, v in stats.items():
    print(f"  {k}: {v}")
print("\nΤop φορείς:\n", df.provider.value_counts().head(10).to_string())
print("\nΑπλές υποψήφιες για Rules as Code (2–5 προϋποθέσεις, λίγα βήματα):")
cand = df[(df.n_req.between(2, 5)) & (df.n_steps.between(1, 6))].head(15)
print(cand[["title", "n_req", "n_steps"]].to_string(index=False))

out = ROOT / "data" / "explore_report.md"
out.write_text("# Εξερεύνηση dataset\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in stats.items())
               + "\n\n## Αντιστοίχιση στηλών\n\n" + "\n".join(f"- {k} ← `{v}`" for k, v in cols.items())
               + "\n\n## Υποψήφιες για Rules as Code\n\n" + cand.to_markdown(index=False), encoding="utf-8")
if not args.sample:
    save_cache(procs)
    print(f"\n→ Αποθηκεύτηκε cache: data/procedures.json")
print(f"→ Αναφορά: {out}")
