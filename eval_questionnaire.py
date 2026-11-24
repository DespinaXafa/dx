"""
Αξιολόγηση ερωτηματολογίου σε 20 τυχαίες διαδικασίες (random.seed(42) πάνω στη σειρά του parquet).

Αυτόματο μέρος : η λογική «και/ή» της εφαρμογής ξαναϋπολογίζεται ΑΝΕΞΑΡΤΗΤΑ από τα ωμά πεδία
                 conditions_alternative / conditions_alternative_of του parquet και συγκρίνεται.
                 Ελέγχεται επίσης ότι κάθε ερώτηση περιέχει αυτούσιο το κείμενο της προϋπόθεσης.
Χειροκίνητο μέρος: eval/questionnaire_review.csv — ανάγνωση κάθε διαδικασίας από άνθρωπο:
                 (α) είναι σωστό το «και/ή» με βάση το νόημα του κειμένου;
                 (β) λέει η ερώτηση ό,τι η προϋπόθεση;
Έξοδος: eval/questionnaire_results.csv + σύνοψη.
"""
import csv, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from core.mitos import PARQUET, load
from core.questionnaire import build, logic_string

def raw_groups(raw):
    """Ανεξάρτητη υλοποίηση: γράφημα συνδέσεων → συνεκτικές συνιστώσες (BFS)."""
    cs = json.loads(raw or "[]"); nums = [c["conditions_num_id"] for c in cs]
    adj = {n: set() for n in nums}
    for i, c in enumerate(cs):
        o = c.get("conditions_alternative_of")
        t = o if o in adj else (nums[i - 1] if c.get("conditions_alternative") and o is None and i > 0 else None)
        if t is not None:
            adj[c["conditions_num_id"]].add(t); adj[t].add(c["conditions_num_id"])
    seen, comps = set(), []
    for n in nums:
        if n in seen: continue
        comp, st = [], [n]
        while st:
            x = st.pop()
            if x in seen: continue
            seen.add(x); comp.append(x); st.extend(adj[x])
        comps.append(sorted(comp))
    return sorted(comps)

P = load(); random.seed(42); S = random.sample(P, 20)
raw = pd.read_parquet(PARQUET).set_index("id")["Προϋποθέσεις"]
review = {r["id"]: r for r in csv.DictReader(open("eval/questionnaire_review.csv", encoding="utf-8"))}
rows = []
for k, p in enumerate(S, 1):
    app = sorted(sorted(g.members) for g in p.groups)
    auto_ok = app == raw_groups(raw[p.id])
    verbatim = all(p.cond(n).text in q.options for q in build(p) for n in q.condition_nums)
    rv = review[p.id]
    rows.append({"#": k, "id": p.id, "title": p.title, "conditions": len(p.conditions),
                 "logic": logic_string(p), "fields_match": "Ναι" if auto_ok else "Όχι",
                 "verbatim": "Ναι" if verbatim else "Όχι", "and_or_correct": rv["and_or_correct"],
                 "question_faithful": rv["question_faithful"], "note": rv["note"]})
with open("eval/questionnaire_results.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
n = len(rows); cnt = lambda k, v: sum(r[k] == v for r in rows)
print(f"Διαδικασίες: {n} · χωρίς προϋποθέσεις: {sum(r['conditions']==0 for r in rows)} · με «ή»: {sum('ή' in r['logic'] for r in rows)}")
print(f"Λογική = πεδία ΜΙΤΟΣ (αυτόματο):    {cnt('fields_match','Ναι')}/{n}")
print(f"Ερωτήσεις με αυτούσιο κείμενο:      {cnt('verbatim','Ναι')}/{n}")
print(f"«Και/ή» σωστό κατά το νόημα:         {cnt('and_or_correct','Ναι')}/{n}")
fa = [r for r in rows if r['question_faithful'] != 'Δ/Υ']
print(f"Ερώτηση = προϋπόθεση (χειροκίνητο):  {sum(r['question_faithful']=='Ναι' for r in fa)}/{len(fa)} Ναι, {sum(r['question_faithful']=='Μερικώς' for r in fa)} Μερικώς")
