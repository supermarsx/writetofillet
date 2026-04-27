#!/usr/bin/env bash
set -euo pipefail
echo "Building writetofillet binary for this platform..."
python -m pip install --upgrade pip
python -m pip install pyinstaller -e .
pyinstaller --onefile -n writetofillet --paths src scripts/pyinstaller_entry.py
echo "Built in ./dist" && ls -lah dist || true
