#!/usr/bin/env bash
# Sets up the Python environment used by the CV PDF pipeline (cv_style.py / cv_pdf.py).
# Usage: scripts/setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${CV_PDF_VENV:-$HOME/.opencode-cv/venv}"

if [ ! -x "$VENV/bin/python" ]; then
  echo "creating venv at $VENV"
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "ready: $VENV/bin/python"