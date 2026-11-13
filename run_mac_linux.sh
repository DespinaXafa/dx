#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements-light.txt
USE_EMBEDDINGS=0 DATA_SOURCE=auto streamlit run app.py
