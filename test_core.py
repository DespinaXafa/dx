"""Έλεγχοι για κανονικοποίηση σχήματος, ερωτηματολόγιο, flowchart και αναζήτηση."""
from core.data import load_sample, _from_records
from core.flowchart import to_mermaid
from core.questionnaire import build, decide
from core.schema import split_sections, to_groups
from core.search import ProcedureSearch


def test_groups_from_nested_lists():
    assert to_groups([["A"], ["B1", "B2"]]) == [["A"], ["B1", "B2"]]


def test_groups_from_dicts_with_alternatives():
    v = [{"text": "Ενήλικος"}, {"alternatives": [{"text": "Έλληνας"}, {"text": "Πολίτης ΕΕ"}]}]
    assert to_groups(v) == [["Ενήλικος"], ["Έλληνας", "Πολίτης ΕΕ"]]


def test_groups_from_text_with_or_lines():
    txt = "- Είστε ενήλικος\n- Έχετε ελληνική υπηκοότητα\n- Ή υπηκοότητα κράτους-μέλους ΕΕ\n- Η αίτηση υποβάλλεται εμπρόθεσμα"
    g = to_groups(txt)
    assert g[0] == ["Είστε ενήλικος"]
    assert g[1] == ["Έχετε ελληνική υπηκοότητα", "υπηκοότητα κράτους-μέλους ΕΕ"]
    assert g[2] == ["Η αίτηση υποβάλλεται εμπρόθεσμα"]   # «Η» άρθρο ≠ «Ή» διάζευξη


def test_text_only_dataset_is_parsed():
    rec = {"text": "# Έκδοση βεβαίωσης ανεργίας\nΣυνοπτική περιγραφή: Βεβαίωση από ΔΥΠΑ\n"
                   "## Προϋποθέσεις\n- Ενήλικος\n- Εγγεγραμμένος στη ΔΥΠΑ\n## Βήματα\n1. Είσοδος\n2. Έκδοση\n"
                   "## Νομοθεσία\n- Ν. 4921/2022"}
    procs, cols = _from_records([rec])
    p = procs[0]
    assert p.title == "Έκδοση βεβαίωσης ανεργίας"
    assert p.requirements == [["Ενήλικος"], ["Εγγεγραμμένος στη ΔΥΠΑ"]]
    assert p.steps == ["Είσοδος", "Έκδοση"] and p.legislation == ["Ν. 4921/2022"]


def test_questionnaire_and_decision():
    p = load_sample()[0][0]
    qs = build(p)
    assert len(qs) == len(p.requirements) and qs[1].kind == "any_of"
    yes = {i: True for i in range(len(qs))}
    assert decide(p, yes).eligible is True
    assert decide(p, {**yes, 0: False}).eligible is False
    assert decide(p, {0: True}).eligible is None


def test_flowchart_has_start_end():
    code = to_mermaid(load_sample()[0][0])
    assert code.startswith("flowchart TD") and "Έναρξη" in code and "Τέλος" in code


def test_search_lexical_finds_unemployment_certificate():
    procs, _ = load_sample()
    eng = ProcedureSearch(procs, use_embeddings=False)
    assert "ανεργίας" in eng.search("θέλω βεβαίωση ανεργίας")[0].proc.title
