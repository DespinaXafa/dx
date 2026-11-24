"""
Αναζήτηση διαδικασιών ΜΟΝΟ στο κείμενο του ΜΙΤΟΣ (τίτλος + περιγραφή).
Δεν προστίθενται δικές μας λέξεις-κλειδιά / συνώνυμα στις διαδικασίες.

Μέθοδοι:
  lexical  : TF-IDF σε n-grams χαρακτήρων (3–5) πάνω σε κείμενο χωρίς τόνους
             (αντέχει στην ελληνική κλίση: ανεργία / ανέργων / άνεργος)
  semantic : multilingual-e5-small embedding του «τίτλος. περιγραφή» + cosine (πρόθεμα query:/passage:).
  semantic_max (δοκιμή/ablation): max(ομοιότητα με τίτλο, ομοιότητα με τίτλο+περιγραφή).
             Δεν βελτίωσε τα αποτελέσματα, οπότε η εφαρμογή χρησιμοποιεί το semantic.
  hybrid   : Reciprocal Rank Fusion (RRF, k=60) lexical + semantic. Το k=60 είναι η τυπική
             τιμή της βιβλιογραφίας. ΔΕΝ ρυθμίστηκε πάνω στις 20 ερωτήσεις αξιολόγησης.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .mitos import Procedure

ROOT = Path(__file__).resolve().parent.parent
EMB = ROOT / "data" / "emb_e5_small.npy"
EMB_TITLE = ROOT / "data" / "emb_e5_small_title.npy"
EMB_IDS = ROOT / "data" / "emb_ids.txt"
RRF_K = 60


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("ς", "σ")


class Search:
    def __init__(self, procs: list[Procedure], encoder=None):
        """encoder: αντικείμενο με .encode(texts, prefix) -> L2-normalized np.ndarray (π.χ. tools/e5.py)."""
        self.procs = procs
        self.tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self.X = self.tfidf.fit_transform([norm(p.search_text()) for p in procs])
        self.encoder = encoder
        self.E = self.ET = None
        if EMB.exists() and EMB_IDS.exists():
            ids = EMB_IDS.read_text().split("\n")
            if ids == [p.id for p in procs]:
                self.E = np.load(EMB)
                self.ET = np.load(EMB_TITLE) if EMB_TITLE.exists() else None

    # --- σκορ ανά μέθοδο
    def lexical_scores(self, q: str) -> np.ndarray:
        return (self.X @ self.tfidf.transform([norm(q)]).T).toarray().ravel()

    def semantic_scores(self, q: str) -> np.ndarray:
        if self.E is None or self.encoder is None:
            raise RuntimeError("Δεν υπάρχουν embeddings ή encoder")
        return self.E @ self.encoder.encode([q], "query: ")[0]

    def semantic_max_scores(self, q: str) -> np.ndarray:
        qv = self.encoder.encode([q], "query: ")[0]
        return np.maximum(self.E @ qv, self.ET @ qv)

    @staticmethod
    def _ranks(scores: np.ndarray) -> np.ndarray:
        order = np.argsort(-scores, kind="stable")
        r = np.empty_like(order)
        r[order] = np.arange(1, len(order) + 1)
        return r

    def scores(self, q: str, method: str = "hybrid") -> np.ndarray:
        if method == "lexical":
            return self.lexical_scores(q)
        if method == "semantic":
            return self.semantic_scores(q)
        if method == "semantic_max":
            return self.semantic_max_scores(q)
        if method == "hybrid":
            lr = self._ranks(self.lexical_scores(q))
            sr = self._ranks(self.semantic_scores(q))
            return 1 / (RRF_K + lr) + 1 / (RRF_K + sr)
        raise ValueError(method)

    def search(self, q: str, k: int = 5, method: str = "hybrid") -> list[tuple[Procedure, float]]:
        s = self.scores(q, method)
        top = np.argsort(-s, kind="stable")[:k]
        return [(self.procs[i], float(s[i])) for i in top]

    def rank_of(self, q: str, pid: str, method: str) -> int:
        s = self.scores(q, method)
        order = np.argsort(-s, kind="stable")
        return int(next(i for i, j in enumerate(order) if self.procs[j].id == pid)) + 1
