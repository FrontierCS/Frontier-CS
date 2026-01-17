#!/usr/bin/env bash
set -euo pipefail

# Prepare problem resources for grammar_fuzzing/sql_parser
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo "[setup] grammar_fuzzing/sql_parser setup starting..." >&2

# Use a fixed venv path inside Docker
VENV_DIR="/work/.venv"
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

# Install uv if not available
pip install --user uv >/dev/null 2>&1 || pip install uv >/dev/null 2>&1 || true

echo "[setup] Creating venv at $VENV_DIR" >&2
uv venv "$VENV_DIR"
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

PROJECT_DIR="$SCRIPT_DIR/resources"
if [[ -f "$PROJECT_DIR/pyproject.toml" ]]; then
  echo "[setup] uv sync project=$PROJECT_DIR" >&2
  uv --project "$PROJECT_DIR" sync --active
else
  echo "[setup] WARNING: pyproject.toml not found at $PROJECT_DIR; skipping dependency sync" >&2
fi

echo "[setup] grammar_fuzzing/sql_parser setup done" >&2
