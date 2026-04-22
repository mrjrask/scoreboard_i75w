#!/usr/bin/env bash
set -euo pipefail

if ! command -v mpremote >/dev/null 2>&1; then
  echo "mpremote not found. Install with: python3 -m pip install --upgrade mpremote"
  exit 1
fi

echo "Copying main.py to connected MicroPython device..."
mpremote fs cp main.py :main.py

if [[ -f secrets.py ]]; then
  echo "Copying secrets.py..."
  mpremote fs cp secrets.py :secrets.py
else
  echo "No secrets.py found in repo root. Skipping Wi-Fi credentials copy."
fi

echo "Resetting device..."
mpremote reset

echo "Done."
