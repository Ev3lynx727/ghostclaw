#!/usr/bin/env bash
# Ghostclaw Compare — Bash wrapper
# Usage: ./scripts/compare.sh --repos-file repos.txt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="${SCRIPT_DIR}/../skill/ghostclaw"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="$SKILL_ROOT:${PYTHONPATH:-}"

"$PYTHON" "$SCRIPT_DIR/compare.py" "$@"
