"""
Κανονικοποίηση εγγραφών του ΜΙΤΟΣ σε ενιαίο σχήμα `Procedure`.

Το dataset glossAPI/mitos μπορεί να έχει:
  (α) ξεχωριστές στήλες (title, requirements, steps, ...) — σε list, dict ή JSON string
  (β) μία στήλη κειμένου (π.χ. "text" σε markdown) με ενότητες «Προϋποθέσεις», «Βήματα», ...
Ο κώδικας ανιχνεύει αυτόματα ποια περίπτωση ισχύει. Αν η αυτόματη ανίχνευση αστοχήσει,
ορίστε τα ονόματα στηλών στο `schema_override.json` (βλ. README, Βήμα 1).

Προϋποθέσεις = λίστα «ομάδων»: AND μεταξύ ομάδων, OR μέσα στην ομάδα (εναλλακτικές).
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------------- helpers

def norm(s: str) -> str:
    """πεζά, χωρίς τόνους, τελικό σ → σ"""
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("ς", "σ").strip()


def clean(s: Any) -> str:
    s = re.sub(r"<[^>]+>", " ", str(s))            # HTML tags
    s = re.sub(r"[*_`#>]+", " ", s)                 # markdown σύμβολα
    s = re.sub(r"^\s*(?:[-•▪●·]|\d+[.)])\s*", "", s)  # bullets / αρίθμηση
    return re.sub(r"\s+", " ", s).strip(" ;:.,")


# ----------------------------------------------------------------------------- model

@dataclass
class Procedure:
    id: str
    title: str
    description: str = ""
    provider: str = ""
    requirements: list[list[str]] = field(default_factory=list)   # [[A], [B1, B2], ...]
    steps: list[str] = field(default_factory=list)
    legislation: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    cost: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    def search_text(self) -> str:
        req = " ".join(x for g in self.requirements for x in g)
        return f"{self.title}. {self.title}. {self.description} {req}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw")
        return d


# ----------------------------------------------------------------------------- column detection

CANDIDATES: dict[str, list[str]] = {
    "id": ["id", "uuid", "procedure_id", "code", "κωδικος"],
    "title": ["title", "official_title", "name", "τιτλοσ", "procedure_title"],
    "description": ["description", "summary", "abstract", "περιγραφη"],
    "provider": ["provider", "organization", "organisation", "authority", "competent_authority",
                 "φορεασ", "αρμοδιοσ φορεασ"],
    "requirements": ["requirements", "conditions", "prerequisites", "criteria", "προυποθεσεισ"],
    "steps": ["steps", "process_steps", "βηματα", "digital_steps"],
    "legislation": ["legislation", "legal_references", "laws", "rules", "νομοθεσια", "νομικο πλαισιο"],
    "documents": ["documents", "evidence", "required_documents", "δικαιολογητικα"],
    "cost": ["cost", "fees", "κοστοσ"],
    "text": ["text", "content", "markdown", "body", "κειμενο"],
}


def detect_columns(columns: list[str], override: dict | None = None) -> dict[str, str | None]:
    override = override or {}
    ncols = {norm(c): c for c in columns}
    out: dict[str, str | None] = {}
    for key, cands in CANDIDATES.items():
        if key in override:
            out[key] = override[key]
            continue
        hit = next((ncols[c] for c in cands if c in ncols), None)
        if hit is None:  # substring match
            hit = next((orig for n, orig in ncols.items() if any(c in n for c in cands)), None)
        out[key] = hit
    return out


# ----------------------------------------------------------------------------- value parsing

ALT_MARKERS = ("εναλλακτικ", "alternative", "alternatives", "options", "any_of", "oneof", "one_of")
ITEM_TEXT_KEYS = ("text", "title", "name", "description", "condition", "value", "label", "περιγραφη")


def _maybe_json(v: Any) -> Any:
    if isinstance(v, str) and v.strip()[:1] in "[{":
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def _item_text(x: Any) -> str:
    if isinstance(x, dict):
        for k in ITEM_TEXT_KEYS:
            for kk, vv in x.items():
                if norm(kk) == k and vv:
                    return clean(vv)
        return clean(" ".join(str(v) for v in x.values() if isinstance(v, str)))
    return clean(x)


def to_list(v: Any) -> list[str]:
    """Οποιαδήποτε τιμή → λίστα από καθαρά strings."""
    v = _maybe_json(v)
    if v is None or (isinstance(v, float) and v != v):
        return []
    if isinstance(v, dict):
        v = next((vv for vv in v.values() if isinstance(vv, list)), [v])
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            out.extend(to_list(x) if isinstance(x, (list, tuple)) else [_item_text(x)])
        return [x for x in out if x]
    return [clean(line) for line in re.split(r"\n+|(?<=;)\s+", str(v)) if clean(line)]


def to_groups(v: Any) -> list[list[str]]:
    """Προϋποθέσεις → λίστα ομάδων (εναλλακτικές μέσα σε ομάδα)."""
    v = _maybe_json(v)
    if v is None or (isinstance(v, float) and v != v):
        return []
    if isinstance(v, (list, tuple)):
        groups: list[list[str]] = []
        for x in v:
            x = _maybe_json(x)
            if isinstance(x, (list, tuple)):                       # [[A],[B1,B2]]
                g = [t for t in (_item_text(y) for y in x) if t]
            elif isinstance(x, dict):
                alt_key = next((k for k in x if any(m in norm(k) for m in ALT_MARKERS)), None)
                if alt_key and isinstance(_maybe_json(x[alt_key]), list):
                    g = to_list(x[alt_key])                       # {"alternatives":[...]}
                else:
                    g = [_item_text(x)]
            else:
                g = [_item_text(x)]
            if g and g[0]:
                groups.append(g)
        return merge_textual_alternatives(groups)
    return text_to_groups(str(v))


# Προσοχή: το «Η» (άρθρο) ≠ «Ή» (διάζευξη) — γι' αυτό ελέγχουμε με τόνο, πριν το norm()
ALT_LINE = re.compile(r"^(ή\s+εναλλακτικά|ή|εναλλακτικά|εναλλακτικώς|or)(?=[\s:,])[:,\s]*", re.I)


def merge_textual_alternatives(groups: list[list[str]]) -> list[list[str]]:
    """Γραμμές που ξεκινούν με «Ή …» / «Εναλλακτικά …» ενώνονται με την προηγούμενη ομάδα."""
    out: list[list[str]] = []
    for g in groups:
        if out and len(g) == 1 and ALT_LINE.match(g[0].lower()):
            out[-1].append(clean(ALT_LINE.sub("", g[0])) or g[0])
        else:
            out.append(list(g))
    return out


def text_to_groups(text: str) -> list[list[str]]:
    lines = [ln for ln in re.split(r"\n+", text) if clean(ln)]
    if len(lines) <= 1:
        lines = [p for p in re.split(r";\s*|\.\s+(?=[Α-ΩΆ-Ώ])", text) if clean(p)]
    return merge_textual_alternatives([[clean(ln)] for ln in lines])


# ----------------------------------------------------------------------------- text sections (case β)

SECTION_ALIASES = {
    "requirements": ["προυποθεσεισ", "προυποθεση", "requirements", "conditions"],
    "steps": ["βηματα", "ψηφιακα βηματα", "steps"],
    "legislation": ["νομοθεσια", "νομικο πλαισιο", "νομικεσ παραπομπεσ", "legislation"],
    "documents": ["δικαιολογητικα", "απαραιτητα δικαιολογητικα", "documents"],
    "description": ["περιγραφη", "συνοπτικη περιγραφη", "description"],
    "provider": ["αρμοδιοσ φορεασ", "φορεασ", "provider"],
    "cost": ["κοστοσ", "cost"],
}


def split_sections(text: str) -> dict[str, str]:
    """Σπάει markdown/plain κείμενο σε ενότητες με βάση επικεφαλίδες."""
    out: dict[str, list[str]] = {}
    current = "_intro"
    for line in str(text).splitlines():
        head = norm(clean(line))
        key = None
        if len(head) < 60:
            for k, aliases in SECTION_ALIASES.items():
                if any(head == a or head.startswith(a + " ") or head.startswith(a + ":") for a in aliases):
                    key = k
                    break
        if key:
            current = key
            rest = line.split(":", 1)[1] if ":" in line else ""
            out.setdefault(current, [])
            if clean(rest):
                out[current].append(rest)
        else:
            out.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


# ----------------------------------------------------------------------------- main entry

def normalize_record(rec: dict, cols: dict[str, str | None], idx: int) -> Procedure:
    get = lambda k: rec.get(cols[k]) if cols.get(k) else None  # noqa: E731
    sections = split_sections(get("text")) if cols.get("text") and get("text") else {}

    def pick(k):
        v = get(k)
        return v if v not in (None, "", []) else sections.get(k)

    title = clean(get("title") or "")
    if not title and sections.get("_intro"):
        title = clean(sections["_intro"].strip().splitlines()[0])
    return Procedure(
        id=str(get("id") or idx),
        title=title or f"Διαδικασία {idx}",
        description=" ".join(to_list(pick("description")))[:1500],
        provider=" ".join(to_list(pick("provider")))[:200],
        requirements=to_groups(pick("requirements")),
        steps=to_list(pick("steps")),
        legislation=to_list(pick("legislation")),
        documents=to_list(pick("documents")),
        cost=" ".join(to_list(pick("cost")))[:200],
        raw=rec,
    )


def load_override(path: str | Path = "schema_override.json") -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
