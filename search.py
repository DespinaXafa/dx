"""
Σημασιολογική αναζήτηση διαδικασιών.

- Κύρια μέθοδος: embeddings με πολυγλωσσικό μοντέλο (multilingual-e5) + cosine similarity.
- Lexical: TF-IDF σε χαρακτήρες (3–5-grams), που αντέχει στην ελληνική μορφολογία
  (ανεργία / ανέργων / άνεργος).
- Hybrid: score = α·semantic + (1-α)·lexical. Αν το μοντέλο δεν φορτώσει, μόνο lexical.

Για ~2–5 χιλ. διαδικασίες αρκεί numpy (brute force)· FAISS χρειάζεται μόνο σε πολύ μεγαλύτερη κλίμακα.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .schema import Procedure, norm

log = logging.getLogger(__name__)
MODEL_NAME = "intfloat/multilingual-e5-small"   # ελαφρύ, τρέχει σε CPU (HF Spaces free)
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Hit:
    proc: Procedure
    score: float
    semantic: float | None
    lexical: float


class ProcedureSearch:
    def __init__(self, procs: list[Procedure], use_embeddings: bool = True, alpha: float = 0.7):
        self.procs = procs
        self.alpha = alpha
        texts = [norm(p.search_text()) for p in procs]

        self.tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1)
        self.X = self.tfidf.fit_transform(texts)

        self.model = None
        self.E = None
        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(MODEL_NAME)
                self.E = self._doc_embeddings([p.search_text() for p in procs])
            except Exception as e:
                log.warning("Embeddings μη διαθέσιμα (%s) — μόνο TF-IDF", e)
                self.model = None

    # -- embeddings με cache στον δίσκο ώστε να υπολογίζονται μία φορά
    def _doc_embeddings(self, texts: list[str]) -> np.ndarray:
        key = hashlib.md5(("|".join(texts) + MODEL_NAME).encode()).hexdigest()[:12]
        f = CACHE_DIR / f"emb_{key}.npy"
        if f.exists():
            return np.load(f)
        E = self.model.encode([f"passage: {t}" for t in texts], normalize_embeddings=True,
                              batch_size=64, show_progress_bar=True)
        E = np.asarray(E, dtype=np.float32)
        np.save(f, E)
        return E

    @property
    def mode(self) -> str:
        return f"hybrid (α={self.alpha}, {MODEL_NAME} + TF-IDF)" if self.model else "lexical (TF-IDF char n-grams)"

    def search(self, query: str, k: int = 5) -> list[Hit]:
        q = self.tfidf.transform([norm(query)])
        lex = (self.X @ q.T).toarray().ravel()          # cosine (τα tf-idf είναι L2-normalized)
        if self.model is not None:
            qv = self.model.encode([f"query: {query}"], normalize_embeddings=True)[0]
            sem = self.E @ qv
            # min-max scaling ώστε να είναι συγκρίσιμα
            s_n = (sem - sem.min()) / (np.ptp(sem) or 1)
            l_n = (lex - lex.min()) / (np.ptp(lex) or 1)
            score = self.alpha * s_n + (1 - self.alpha) * l_n
        else:
            sem, score = None, lex
        top = np.argsort(-score)[:k]
        return [Hit(self.procs[i], float(score[i]), None if sem is None else float(sem[i]), float(lex[i]))
                for i in top]
