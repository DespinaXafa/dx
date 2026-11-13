@echo off
REM ============================================================
REM  MITOS Rules as Code - run the app locally (Windows)
REM  Double-click this file. First run takes a few minutes.
REM ============================================================
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ from https://www.python.org/downloads/
  echo IMPORTANT: tick "Add python.exe to PATH" during installation.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo Installing packages (first run only)...
python -m pip install --upgrade pip >nul
pip install -r requirements-light.txt

REM Light mode: TF-IDF search, real MITOS dataset if internet is available.
REM For full semantic search: pip install -r requirements.txt and set USE_EMBEDDINGS=1
set USE_EMBEDDINGS=0
set DATA_SOURCE=auto

echo Starting app at http://localhost:8501 ...
streamlit run app.py
pause
