"""Κατεβάζει ό,τι δεν ανεβαίνει στο GitHub: το dataset ΜΙΤΟΣ και το μοντέλο e5 (ONNX).
Το glossAPI/mitos είναι gated: αποδεχτείτε τους όρους στη σελίδα του dataset στο Hugging Face
και κάντε `huggingface-cli login` (ή ορίστε HF_TOKEN) πριν το τρέξετε.
Χρήση: python tools/get_data.py
"""
import shutil
from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files

ROOT = Path(__file__).resolve().parent.parent
data = ROOT / "data"; data.mkdir(exist_ok=True)
pq = [f for f in list_repo_files("glossAPI/mitos", repo_type="dataset") if f.endswith(".parquet")][0]
shutil.copy(hf_hub_download("glossAPI/mitos", pq, repo_type="dataset"), data / "mitos.parquet")
print("ok  data/mitos.parquet")
mdir = ROOT / "models" / "e5"; mdir.mkdir(parents=True, exist_ok=True)
for src, dst in [("onnx/model_quantized.onnx", "model_quantized.onnx"), ("tokenizer.json", "tokenizer.json")]:
    shutil.copy(hf_hub_download("Xenova/multilingual-e5-small", src), mdir / dst)
print("ok  models/e5/  (για: --model-dir models/e5)")
