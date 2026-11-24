import sys, time, numpy as np
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from e5 import E5
from core.mitos import load
P = load(); m = E5(sys.argv[1]); t = time.time()
E = m.encode([p.title for p in P], "passage: ", batch=64)
np.save("data/emb_e5_small_title.npy", E); print(E.shape, round(time.time() - t), "s")
