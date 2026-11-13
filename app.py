"""
Έλεγχος Προϋποθέσεων Διοικητικών Διαδικασιών — Rules as Code με βάση το ΜΙΤΟΣ
Εκτέλεση:  streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.data import load_procedures
from core.evaluation import eval_retrieval, eval_rules, load_queries
from core.flowchart import mermaid_html, to_mermaid
from core.questionnaire import build, decide
from core.rules.unemployment_certificate import (MIN_AGE, PROCEDURE_TITLE_HINT, RULES, Citizen,
                                                 Citizenship, is_eligible)
from core.schema import norm
from core.search import ProcedureSearch

st.set_page_config(page_title="ΜΙΤΟΣ · Rules as Code", page_icon="🧾", layout="wide")

USE_EMB = os.getenv("USE_EMBEDDINGS", "1") == "1"


@st.cache_resource(show_spinner="Φόρτωση διαδικασιών & ευρετηρίου…")
def get_engine():
    procs, src = load_procedures(os.getenv("DATA_SOURCE", "auto"))
    return ProcedureSearch(procs, use_embeddings=USE_EMB), src


engine, source = get_engine()
procs = engine.procs

st.title("🧾 Έλεγχος Προϋποθέσεων Διοικητικών Διαδικασιών")
st.caption(f"Rules as Code με βάση το ΜΙΤΟΣ · πηγή: **{source}** · {len(procs)} διαδικασίες · "
           f"αναζήτηση: {engine.mode}")

tab_app, tab_rac, tab_eval, tab_data = st.tabs(
    ["🔎 Αναζήτηση & έλεγχος", "⚖️ Rules as Code", "📊 Αξιολόγηση", "🗂️ Dataset"])


def draw_flow(proc, height=520):
    code = to_mermaid(proc)
    html = mermaid_html(code)
    if hasattr(st, "iframe"):            # Streamlit ≥ 1.5x
        st.iframe(html, height=height)
    else:                                # παλαιότερες εκδόσεις
        components.html(html, height=height, scrolling=True)
    with st.expander("Κώδικας Mermaid"):
        st.code(code, language="text")


# ============================================================ 1. ΑΝΑΖΗΤΗΣΗ + ΕΡΩΤΗΜΑΤΟΛΟΓΙΟ
with tab_app:
    q = st.text_input("Τι χρειάζεστε;", value="θέλω βεβαίωση ανεργίας",
                      placeholder="π.χ. έχασα τη δουλειά μου, μετακόμισα, θέλω διαβατήριο")
    if q:
        hits = engine.search(q, k=5)
        left, right = st.columns([1, 2])
        with left:
            st.subheader("Σχετικές διαδικασίες")
            labels = [f"{h.proc.title}  ·  {h.score:.2f}" for h in hits]
            choice = st.radio("Επιλέξτε:", range(len(hits)), format_func=lambda i: labels[i],
                              label_visibility="collapsed")
            with st.expander("Βαθμολογίες (semantic / lexical)"):
                st.dataframe(pd.DataFrame([{"διαδικασία": h.proc.title, "τελικό": round(h.score, 3),
                                            "semantic": None if h.semantic is None else round(h.semantic, 3),
                                            "lexical": round(h.lexical, 3)} for h in hits]),
                             hide_index=True)
        proc = hits[choice].proc
        with right:
            st.subheader(proc.title)
            meta = " · ".join(x for x in [proc.provider, proc.cost] if x)
            if meta:
                st.caption(meta)
            if proc.description:
                st.write(proc.description)
            if proc.legislation:
                st.markdown("**Νομοθεσία:** " + " · ".join(proc.legislation[:6]))

            st.markdown("### Πληρώ τις προϋποθέσεις;")
            questions = build(proc)
            if not questions:
                st.info("Δεν έχουν καταγραφεί προϋποθέσεις για αυτή τη διαδικασία.")
            answers = {}
            for qq in questions:
                key = f"{proc.id}_{qq.idx}"
                if qq.kind == "yesno":
                    a = st.radio(f"{qq.idx + 1}. {qq.text}", ["Ναι", "Όχι"], index=None,
                                 horizontal=True, key=key)
                    answers[qq.idx] = None if a is None else a == "Ναι"
                else:
                    opts = qq.options + ["Κανένα από τα παραπάνω"]
                    a = st.radio(f"{qq.idx + 1}. {qq.text}", opts, index=None, key=key)
                    answers[qq.idx] = None if a is None else a != opts[-1]
            if questions:
                v = decide(proc, answers)
                if v.eligible is False:
                    st.error("✗ **Δεν πληρούνται οι προϋποθέσεις**\n\n" + "\n".join(f"- {f}" for f in v.failed))
                elif v.eligible is True:
                    st.success("✓ **Πληρούνται οι προϋποθέσεις.** Συνεχίστε με τα βήματα παρακάτω.")
                else:
                    st.info(f"Απομένουν {len(v.unanswered)} ερωτήσεις.")
                st.caption("Η απάντηση είναι ενδεικτική και δεν αποτελεί διοικητική πράξη.")

            st.markdown("### Βήματα διαδικασίας")
            draw_flow(proc)

# ============================================================ 2. RULES AS CODE
with tab_rac:
    st.subheader("«Έκδοση βεβαίωσης ανεργίας»: προϋποθέσεις ως εκτελέσιμος κώδικας")
    match = next((p for p in procs if PROCEDURE_TITLE_HINT in norm(p.title)), None)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Δοκιμάστε έναν πολίτη**")
        age = st.number_input("Ηλικία", 0, 120, 34)
        cit = st.selectbox("Υπηκοότητα", list(Citizenship),
                           format_func={"GR": "Ελληνική", "EU": "Κράτους-μέλους ΕΕ", "TCN": "Τρίτης χώρας"}.get)
        perm = st.checkbox("Άδεια διαμονής με πρόσβαση στην εργασία", disabled=cit != Citizenship.TCN)
        reg = st.checkbox("Εγγεγραμμένος στο Μητρώο Ανέργων ΔΥΠΑ", value=True)
        emp = st.checkbox("Απασχολείται (μισθωτός / ελ. επαγγελματίας)")
        ret = st.checkbox("Συνταξιούχος γήρατος")
        d = is_eligible(Citizen(age, cit, perm, reg, emp, ret))
        (st.success if d.eligible else st.error)(d.explain())
    with c2:
        st.markdown("**Κανόνες**")
        c = Citizen(age, cit, perm, reg, emp, ret)
        st.dataframe(pd.DataFrame([{"κωδ.": r.id, "κανόνας": r.description, "νομική βάση": r.legal_basis,
                                    "": "✓" if r.check(c) else "✗"} for r in RULES]), hide_index=True)
        if match:
            with st.expander(f"Προϋποθέσεις όπως καταγράφονται στο dataset: {match.title}"):
                for g in match.requirements:
                    st.markdown("- " + " **ή** ".join(g))
    with st.expander("Πηγαίος κώδικας κανόνων"):
        st.code(open("core/rules/unemployment_certificate.py", encoding="utf-8").read(), language="python")

    st.markdown("#### Έλεγχος ορθότητας σε 10 παραδείγματα")
    acc, rows = eval_rules()
    st.metric("Ακρίβεια", f"{acc:.0%}", f"{sum(r['pass'] for r in rows)}/{len(rows)} PASS")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

# ============================================================ 3. ΑΞΙΟΛΟΓΗΣΗ
with tab_eval:
    st.subheader("Αξιολόγηση αναζήτησης")
    st.caption("Ερωτήσεις πολιτών με ground truth (eval/queries.csv). Σωστό = ο τίτλος της διαδικασίας "
               "περιέχει τη στήλη expected_title_contains.")
    m, rows = eval_retrieval(engine, load_queries())
    cols = st.columns(4)
    for col, k in zip(cols, ["Hit@1", "Hit@3", "Hit@5", "MRR"]):
        col.metric(k, f"{m[k]:.2f}")
    st.dataframe(pd.DataFrame([{"ερώτηση": r.query, "αναμενόμενο": r.expected, "θέση": r.rank or "—",
                                "1η πρόταση": r.top1} for r in rows]), hide_index=True, width="stretch")
    st.subheader("Αξιολόγηση με χρήστες")
    st.markdown("""
- 5–10 χρήστες × 3 σενάρια (π.χ. «χάσατε τη δουλειά σας», «μετακομίσατε», «θέλετε διαβατήριο»)
- Μετράμε: εύρεση σωστής διαδικασίας στο top-3, % ερωτήσεων που απαντήθηκαν χωρίς διευκρίνιση,
  χρόνο ολοκλήρωσης, **SUS** score, και συμφωνία ερωτηματολογίου ↔ Rules as Code για τη βεβαίωση ανεργίας.
""")

# ============================================================ 4. DATASET
with tab_data:
    df = pd.DataFrame([{"τίτλος": p.title, "φορέας": p.provider, "προϋποθέσεις": len(p.requirements),
                        "με εναλλακτικές": any(len(g) > 1 for g in p.requirements),
                        "βήματα": len(p.steps), "νομοθεσία": len(p.legislation)} for p in procs])
    c = st.columns(4)
    c[0].metric("Διαδικασίες", len(df))
    c[1].metric("Μ.ό. προϋποθέσεων", f"{df['προϋποθέσεις'].mean():.1f}")
    c[2].metric("Με εναλλακτικές", f"{df['με εναλλακτικές'].mean():.0%}")
    c[3].metric("Μ.ό. βημάτων", f"{df['βήματα'].mean():.1f}")
    st.dataframe(df, hide_index=True, width="stretch")
    sel = st.selectbox("Δείτε μία εγγραφή (κανονικοποιημένη)", range(len(procs)),
                       format_func=lambda i: procs[i].title)
    st.json(procs[sel].to_dict())
