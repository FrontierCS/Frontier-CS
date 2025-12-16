#!/usr/bin/env bash
set -euo pipefail

# Usage: ./set_up_env.sh [config_path]

CONFIG_PATH=${1:-config.yaml}
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Error: config file not found at $CONFIG_PATH" >&2
  exit 1
fi

PROBLEM_DIR=$(pwd)
EXEC_ROOT="/work/execution_env"
mkdir -p "$EXEC_ROOT"

# Parse config for uv project (datasets unused for this problem)
UV_PROJECT_REL=$(
  python3 - <<'PY' "$CONFIG_PATH"
import json, sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())
print(cfg.get("dependencies", {}).get("uv_project", ""))
PY
)

# Install uv if needed
if ! command -v uv >/dev/null 2>&1; then
  echo "[imagenet_pareto setup] Installing uv..."
  pip install --user uv || exit 1
  export PATH="$HOME/.local/bin:$PATH"
fi

# Create virtual environment
VENV_DIR="$EXEC_ROOT/.venv"
echo "[imagenet_pareto setup] Creating venv at $VENV_DIR"
uv venv "$VENV_DIR"
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

# Sync project dependencies
if [[ -n "$UV_PROJECT_REL" ]]; then
  UV_PROJECT_PATH="$PROBLEM_DIR/$UV_PROJECT_REL"
  if [[ ! -f "$UV_PROJECT_PATH/pyproject.toml" ]]; then
    echo "Error: uv project path $UV_PROJECT_PATH missing pyproject.toml" >&2
    exit 1
  fi
  echo "[imagenet_pareto setup] Syncing dependencies from $UV_PROJECT_PATH"
  uv --project "$UV_PROJECT_PATH" sync --active
else
  echo "[imagenet_pareto setup] No uv project specified; installing torch manually"
  uv pip install "torch>=2.2,<2.4" "numpy>=1.24"
fi

echo "[imagenet_pareto setup] Ensuring core runtime dependencies"
uv pip install --upgrade --quiet "numpy>=1.24" "torch>=2.2,<2.4" "tqdm>=4.64"

echo "[imagenet_pareto setup] Environment setup completed successfully"
