"""Εξάγει τα δεδομένα της online εφαρμογής (index.html): data/procs.json και data/emb.bin (e5, int8)."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.mitos import load

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"; OUT.mkdir(parents=True, exist_ok=True)
P = load()
rows = []
for p in P:
    rows.append({
        "id": p.id, "t": p.title, "d": p.description, "o": p.provider, "c": p.cost, "tm": p.time,
        "k": [[c.num, c.text, c.ctype] for c in p.conditions],
        "g": [[g.members, 1 if "alt_unlinked" in g.flags else 0] for g in p.groups],
        "s": [[s["num"], s["title"], 1 if s["child"] else 0, s["previous"], 1 if s["exit"] else 0] for s in p.steps],
        "l": [[(l["type"] + " " + "/".join(x for x in (l["number"], l["year"]) if x)).strip()
               + (f", άρθ. {l['article']}" if l["article"] else ""), l["url"]] for l in p.legislation][:5],
        "n": p.documents,
    })
(OUT / "procs.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
emb = ROOT / "data" / "emb_e5_small.npy"
if emb.exists():
    E = np.load(emb)
    q = np.clip(np.round(E * 127), -127, 127).astype(np.int8)   # int8 ποσοτικοποίηση (~1.7 MB)
    (OUT / "emb.bin").write_bytes(q.tobytes())
    print("emb.bin", q.shape)
print("procs.json", round((OUT / "procs.json").stat().st_size / 1e6, 2), "MB")
