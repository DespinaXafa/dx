"""Βήματα διαδικασίας → διάγραμμα ροής σε Mermaid."""
from __future__ import annotations

import re

from .schema import Procedure

CHECK_WORDS = re.compile(r"(έλεγχ|εξέταση|αξιολόγ|διασταύρωση|έγκριση|γνωμοδότ)", re.I)


def _esc(s: str, n: int = 70) -> str:
    # το κείμενο προέρχεται από το dataset → αφαιρούμε χαρακτήρες που σπάνε το Mermaid/HTML
    s = re.sub(r'[<>{}\[\]|"`]', " ", s.replace("\n", " "))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def to_mermaid(proc: Procedure) -> str:
    lines = ["flowchart TD", 'S(["Έναρξη"])']
    prev, edge = "S", ""
    if not proc.steps:
        lines += ['X["Δεν έχουν καταγραφεί βήματα"]', "S-->X"]
        return "\n".join(lines)
    for i, step in enumerate(proc.steps):
        n = f"N{i}"
        lines += [f'{n}["{i + 1}. {_esc(step)}"]', f"{prev}-->{edge}{n}"]
        prev, edge = n, ""
        # βήματα ελέγχου → ρόμβος απόφασης με κλάδο απόρριψης/διόρθωσης
        if CHECK_WORDS.search(step):
            d = f"D{i}"
            lines += [f'{d}{{"Εγκρίνεται;"}}', f"{n}-->{d}",
                      f'{d}-- Όχι -->R{i}["Συμπλήρωση / απόρριψη"]', f"R{i}-.->{n}"]
            prev, edge = d, "|Ναι| "
    lines += ['E(["Τέλος"])', f"{prev}-->{edge}E"]
    return "\n".join(lines)


def mermaid_html(code: str, height: int = 600) -> str:
    return f"""
<div class="mermaid">{code}</div>
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
mermaid.initialize({{startOnLoad: true, securityLevel: "strict", theme: "default", flowchart: {{curve: "basis"}}}});
</script>"""
