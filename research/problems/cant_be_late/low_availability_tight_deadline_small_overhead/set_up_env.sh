#!/usr/bin/env bash
set -euo pipefail

# Usage: ./set_up_env.sh [config_path]

# Install pyyaml for config parsing (not in base python:3.11-slim image)
pip install pyyaml --quiet 2>/dev/null || pip3 install pyyaml --quiet 2>/dev/null || true

CONFIG_PATH=${1:-config.yaml}
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Error: config file not found at $CONFIG_PATH" >&2
  exit 1
fi

PROBLEM_DIR=$(pwd)
# Use resources directory for venv (problem-specific)
EXEC_ROOT="./resources"
mkdir -p "$EXEC_ROOT"

# Parse config: first line uv_project (may be empty), subsequent lines dataset JSON objects.
CONFIG_LINES=()
while IFS= read -r line; do
    CONFIG_LINES+=("$line")
done < <(python3 - <<'PY' "$CONFIG_PATH"
import json, sys, yaml
from pathlib import Path
cfg_path = Path(sys.argv[1])
content = cfg_path.read_text()
try:
    data = yaml.safe_load(content)
except:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Failed to parse {cfg_path}: {e}")
print(data.get("dependencies", {}).get("uv_project", ""))
for dataset in data.get("datasets", []):
    print(json.dumps(dataset))
PY
)

if [[ ${#CONFIG_LINES[@]} -eq 0 ]]; then
  echo "Error: config ${CONFIG_PATH} is empty or invalid" >&2
  exit 1
fi

UV_PROJECT_REL=${CONFIG_LINES[0]}
DATASET_LINES=("${CONFIG_LINES[@]:1}")

VENV_DIR="$EXEC_ROOT/.venv"

echo "[prepare_env] Creating/updating venv at $VENV_DIR"
uv venv "$VENV_DIR"
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

if [[ -n "$UV_PROJECT_REL" ]]; then
  UV_PROJECT_PATH=$(python3 - <<'PY' "$UV_PROJECT_REL"
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
)
  if [[ ! -f "$UV_PROJECT_PATH/pyproject.toml" ]]; then
    echo "Error: uv project path $UV_PROJECT_REL (resolved to $UV_PROJECT_PATH) missing pyproject.toml" >&2
    exit 1
  fi
  echo "[prepare_env] uv sync project=$UV_PROJECT_PATH"
  uv --project "$UV_PROJECT_PATH" sync --active
else
  echo "[prepare_env] No uv project specified; skipping dependency sync"
fi

# Helper to decode dataset json fields
decode_dataset_field() {
  local json_input="$1"
  local key="$2"
  python3 - <<'PY' "$json_input" "$key"
import json, sys
obj = json.loads(sys.argv[1])
print(obj.get(sys.argv[2], ""))
PY
}

for dataset_json in "${DATASET_LINES[@]}"; do
  [[ -z "$dataset_json" ]] && continue
  dataset_type=$(decode_dataset_field "$dataset_json" "type")
  dataset_path_rel=$(decode_dataset_field "$dataset_json" "path")
  target_rel=$(decode_dataset_field "$dataset_json" "target")
  expected_glob_pattern=$(decode_dataset_field "$dataset_json" "expected_glob")

  case "$dataset_type" in
    local_tar)
      if [[ -z "$dataset_path_rel" || -z "$target_rel" ]]; then
        echo "Error: dataset entry missing path or target: $dataset_json" >&2
        exit 1
      fi
      TAR_PATH="$PROBLEM_DIR/$dataset_path_rel"
      TARGET_DIR="$PROBLEM_DIR/$target_rel"
      mkdir -p "$TARGET_DIR"
      has_expected=false
      if [[ -n "$expected_glob_pattern" ]]; then
        if compgen -G "$TARGET_DIR/$expected_glob_pattern" >/dev/null 2>&1; then
          has_expected=true
        fi
      else
        # If no glob provided, check directory non-empty
        if [[ -n $(ls -A "$TARGET_DIR" 2>/dev/null) ]]; then
          has_expected=true
        fi
      fi
      if $has_expected; then
        echo "[prepare_env] Dataset already present at $TARGET_DIR"
        continue
      fi

      # Check if dataset is available in mounted /datasets folder
      MOUNTED_DATASETS="/datasets/cant_be_late"
      if [[ -d "$MOUNTED_DATASETS" ]] && compgen -G "$MOUNTED_DATASETS/real/ddl=search+task=48+overhead=*/real/*/traces/random_start/*.json" >/dev/null 2>&1; then
        echo "[prepare_env] Using pre-downloaded dataset from $MOUNTED_DATASETS"
        # Create symlinks to mounted datasets instead of copying
        ln -sf "$MOUNTED_DATASETS"/* "$TARGET_DIR/"
        continue
      fi

      if [[ ! -f "$TAR_PATH" ]]; then
        echo "Error: dataset tarball missing at $TAR_PATH" >&2
        exit 1
      fi
      echo "[prepare_env] Extracting $TAR_PATH → $TARGET_DIR"
      tar -xzf "$TAR_PATH" -C "$TARGET_DIR" 2>/dev/null || true
      if [[ -n "$expected_glob_pattern" ]] && ! compgen -G "$TARGET_DIR/$expected_glob_pattern" >/dev/null 2>&1; then
        echo "Error: expected files matching $TARGET_DIR/$expected_glob_pattern not found after extraction" >&2
        exit 1
      fi
      ;;
    *)
      echo "Error: unsupported dataset type '$dataset_type' in $dataset_json" >&2
      exit 1
      ;;
  esac
done

echo "[prepare_env] Completed."
