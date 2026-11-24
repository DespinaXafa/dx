#!/usr/bin/env bash
# Ανοίγει την εφαρμογή τοπικά: http://localhost:8000
cd "$(dirname "$0")"
echo "Ανοίξτε http://localhost:8000"
python3 -m http.server 8000
