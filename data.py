"""Φόρτωση του dataset glossAPI/mitos (ή του τοπικού δείγματος) και κανονικοποίηση."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .schema import Procedure, detect_columns, load_override, normalize_record

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "procedures.json"
SAMPLE = ROOT / "data" / "sample_procedures.json"
HF_DATASET = "glossAPI/mitos"


def _from_records(records: list[dict], override: dict | None = None) -> tuple[list[Procedure], dict]:
    cols = detect_columns(list(records[0].keys()), override) if records else {}
    procs = [normalize_record(r, cols, i) for i, r in enumerate(records)]
    procs = [p for p in procs if p.title]
    # αφαίρεση διπλοτύπων τίτλων
    seen, uniq = set(), []
    for p in procs:
        if p.title not in seen:
            seen.add(p.title)
            uniq.append(p)
    return uniq, cols


def load_hf(split: str = "train", limit: int | None = None) -> tuple[list[Procedure], dict]:
    from datasets import load_dataset  # lazy import

    ds = load_dataset(HF_DATASET, split=split)
    if limit:
        ds = ds.select(range(min(limit, len(ds))))
    return _from_records(ds.to_list(), load_override(ROOT / "schema_override.json"))


def load_sample() -> tuple[list[Procedure], dict]:
    return _from_records(json.loads(SAMPLE.read_text(encoding="utf-8")))


def save_cache(procs: list[Procedure]) -> None:
    CACHE.write_text(json.dumps([p.to_dict() for p in procs], ensure_ascii=False, indent=1), encoding="utf-8")


def load_procedures(source: str = "auto") -> tuple[list[Procedure], str]:
    """
    source: "auto" → cache → Hugging Face → δείγμα
            "hf" | "cache" | "sample"
    Επιστρέφει (διαδικασίες, ετικέτα πηγής).
    """
    if source in ("auto", "cache") and CACHE.exists():
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        return [Procedure(**d) for d in data], f"cache ({CACHE.name})"
    if source in ("auto", "hf"):
        try:
            procs, _ = load_hf()
            save_cache(procs)
            return procs, f"Hugging Face: {HF_DATASET}"
        except Exception as e:  # offline, αλλαγή σχήματος κ.λπ.
            log.warning("Αποτυχία φόρτωσης %s: %s — χρήση δείγματος", HF_DATASET, e)
            if source == "hf":
                raise
    procs, _ = load_sample()
    return procs, "τοπικό δείγμα (sample_procedures.json)"
