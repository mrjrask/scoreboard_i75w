#!/usr/bin/env bash
set -euo pipefail

if ! command -v mpremote >/dev/null 2>&1; then
  echo "mpremote not found. Install with: python3 -m pip install --upgrade mpremote"
  exit 1
fi

echo "Removing files from connected MicroPython device..."
mpremote fs rm :main.py || true
mpremote fs rm :secrets.py || true

echo "Resetting device..."
mpremote reset

echo "Done."
