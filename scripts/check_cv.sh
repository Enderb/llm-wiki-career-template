#!/usr/bin/env bash
# Run every quality check on tailored CVs and print a pass/fail report.
#
# Usage:
#   scripts/check_cv.sh                                   # every CV in the vault
#   scripts/check_cv.sh 20_Wiki/Career/Applications/Acme/CV_Acme_Role.md [more.md ...]
#   scripts/check_cv.sh --no-llm <cv.md>                  # skip the LLM judge
#   scripts/check_cv.sh --llm-only <cv.md>                # only the LLM judge
#
# Environment:
#   CV_JUDGE_BACKEND=anthropic|claude|opencode   force the LLM-judge backend (default: auto)
#   CV_JUDGE_MODEL=<model>                       override the judge model
#   CV_JUDGE_NO_CACHE=1                          ignore cached judge verdicts
#   CV_MAX_WORDS / CV_MAX_PAGES                  override the length limits
#   CV_PDF_VENV=<path>                           Python venv (default ~/.opencode-cv/venv)
#
# Exit code 0 = every check passed. A CV only counts as done when this passes
# with no FAIL (and no SKIP on the LLM judge).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(dirname "$SCRIPT_DIR")"
VENV="${CV_PDF_VENV:-$HOME/.opencode-cv/venv}"
PY="$VENV/bin/python"

if [ ! -x "$PY" ] || ! "$PY" -c "import pytest, pdfminer, reportlab" 2>/dev/null; then
  echo "The checks need the CV venv with pytest installed. Run: scripts/setup.sh" >&2
  exit 2
fi

args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --no-llm) args+=(-m "not llm") ;;
    --llm-only) args+=(-m "llm") ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    -k|-m) args+=("$1" "$2"); shift ;;   # pytest options that take a value
    -*) args+=("$1") ;;
    *) args+=(--cv "$1") ;;
  esac
  shift
done

cd "$VAULT"
exec "$PY" -m pytest tests -q --no-header --tb=no -rN -p no:cacheprovider ${args[@]+"${args[@]}"}
