"""Υπολογίζει e5 embeddings για τίτλο+περιγραφή κάθε διαδικασίας (passage:)."""
import sys, time, numpy as np
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from e5 import E5
from core.mitos import load
P = load()
m = E5(sys.argv[1])
t = time.time()
E = m.encode([p.search_text() for p in P], "passage: ", batch=16)
np.save("data/emb_e5_small.npy", E)
open("data/emb_ids.txt", "w").write("\n".join(p.id for p in P))
print(E.shape, round(time.time() - t), "s")
