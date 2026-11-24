"""
Αξιολόγηση αναζήτησης στο ΠΡΑΓΜΑΤΙΚΟ ΜΙΤΟΣ (4.340 διαδικασίες).
20 ερωτήσεις πολιτών (eval/search_queries.csv) με τη σωστή διαδικασία (id), γραμμένες ΠΡΙΝ
τρέξει οποιαδήποτε αναζήτηση. Η αναζήτηση βλέπει ΜΟΝΟ τίτλο + περιγραφή του ΜΙΤΟΣ.

Μετρικές: Hit@5 (κύρια, όπως ζητήθηκε), Hit@1, Hit@10, MRR.
Χρήση: python scripts/eval_search.py [--model-dir <φάκελος e5 onnx>]
       Χωρίς --model-dir: lexical πάντα· semantic/hybrid αν υπάρχει sentence-transformers.
"""
import argparse, csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.mitos import load
from core.search import Search

ap = argparse.ArgumentParser(); ap.add_argument("--model-dir"); a = ap.parse_args()
enc = None
if a.model_dir:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    from e5 import E5; enc = E5(a.model_dir)
else:
    try:
        from sentence_transformers import SentenceTransformer
        class ST:
            m = SentenceTransformer("intfloat/multilingual-e5-small")
            def encode(self, t, prefix): return self.m.encode([prefix + x for x in t], normalize_embeddings=True)
        enc = ST()
    except Exception as e:
        print("(χωρίς μοντέλο: μόνο lexical)", e)

P = load(); S = Search(P, enc); title = {p.id: p.title for p in P}
Q = list(csv.DictReader(open("eval/search_queries.csv", encoding="utf-8")))
methods = ["lexical"] + (["semantic", "hybrid"] if enc is not None and S.E is not None else []) \
    + (["semantic_max"] if enc is not None and S.ET is not None else [])
rows, summary = [], {}
for m in methods:
    ranks = [S.rank_of(q["query"], q["correct_id"], m) for q in Q]
    summary[m] = {"Hit@1": sum(r == 1 for r in ranks), "Hit@5": sum(r <= 5 for r in ranks),
                  "Hit@10": sum(r <= 10 for r in ranks), "MRR": round(sum(1 / r for r in ranks) / len(ranks), 3)}
    for q, r in zip(Q, ranks):
        top1 = S.search(q["query"], 1, m)[0][0]
        rows.append({"method": m, "query": q["query"], "correct_id": q["correct_id"],
                     "correct_title": title[q["correct_id"]], "rank": r, "top1_id": top1.id, "top1_title": top1.title})
with open("eval/search_results.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"{'μέθοδος':10s} Hit@1  Hit@5  Hit@10  MRR   (n={len(Q)})")
for m, s in summary.items():
    print(f"{m:10s} {s['Hit@1']:>2}/20  {s['Hit@5']:>2}/20  {s['Hit@10']:>2}/20  {s['MRR']}")
