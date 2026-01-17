#!/usr/bin/env bash
set -euo pipefail

# Dependencies are auto-installed by framework via config.yaml uv_project
# This script only handles dataset preparation

CONFIG_PATH=${1:-config.yaml}
PROBLEM_DIR=$(pwd)

# Parse datasets from config (pyyaml is installed by framework)
DATASET_LINES=()
while IFS= read -r line; do
    DATASET_LINES+=("$line")
done < <(python3 - <<'PY' "$CONFIG_PATH"
import json, sys, yaml
from pathlib import Path
data = yaml.safe_load(Path(sys.argv[1]).read_text())
for dataset in data.get("datasets", []):
    print(json.dumps(dataset))
PY
)

[[ ${#DATASET_LINES[@]} -eq 0 ]] && { echo "[cant_be_late] No datasets to prepare"; exit 0; }

get_field() {
  python3 -c "import json, sys; print(json.loads(sys.argv[1]).get(sys.argv[2], ''))" "$1" "$2"
}

for dataset_json in "${DATASET_LINES[@]}"; do
  [[ -z "$dataset_json" ]] && continue

  dtype=$(get_field "$dataset_json" "type")
  path_rel=$(get_field "$dataset_json" "path")
  target_rel=$(get_field "$dataset_json" "target")
  expected_glob=$(get_field "$dataset_json" "expected_glob")

  case "$dtype" in
    local_tar)
      TAR_PATH="$PROBLEM_DIR/$path_rel"
      TARGET_DIR="$PROBLEM_DIR/$target_rel"
      mkdir -p "$TARGET_DIR"

      # Check if already present
      if [[ -n "$expected_glob" ]] && compgen -G "$TARGET_DIR/$expected_glob" &>/dev/null; then
        echo "[cant_be_late] Dataset already present"
        continue
      fi

      # Check mounted datasets
      MOUNTED="/datasets/cant_be_late"
      if [[ -d "$MOUNTED" ]] && compgen -G "$MOUNTED/real/ddl=search+task=48+overhead=*/real/*/traces/random_start/*.json" &>/dev/null; then
        echo "[cant_be_late] Using pre-downloaded dataset from $MOUNTED"
        ln -sf "$MOUNTED"/* "$TARGET_DIR/"
        continue
      fi

      # Extract local tar
      if [[ -f "$TAR_PATH" ]]; then
        echo "[cant_be_late] Extracting $TAR_PATH"
        tar -xzf "$TAR_PATH" -C "$TARGET_DIR" 2>/dev/null || true
      else
        echo "Warning: Dataset tarball not found at $TAR_PATH" >&2
      fi
      ;;
    *)
      echo "Error: Unsupported dataset type: $dtype" >&2
      exit 1
      ;;
  esac
done

echo "[cant_be_late] Dataset preparation complete"
