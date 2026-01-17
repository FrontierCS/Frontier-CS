#!/usr/bin/env bash
set -euo pipefail

# Dependencies are auto-installed by framework via config.yaml uv_project
# This script only handles dataset preparation

CONFIG_PATH=${1:-config.yaml}
PROBLEM_DIR=$(pwd)

# Parse datasets from config
DATASET_LINES=()
while IFS= read -r line; do
    DATASET_LINES+=("$line")
done < <(python3 - <<'PY' "$CONFIG_PATH"
import json, sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())
for dataset in cfg.get("datasets", []):
    print(json.dumps(dataset))
PY
)

[[ ${#DATASET_LINES[@]} -eq 0 ]] && { echo "[vdb setup] No datasets to prepare"; exit 0; }

get_field() {
  python3 -c "import json, sys; print(json.loads(sys.argv[1]).get(sys.argv[2], ''))" "$1" "$2"
}

download_file() {
  local url="$1" dest="$2"
  if command -v wget &>/dev/null; then
    wget -q -O "$dest" "$url"
  elif command -v curl &>/dev/null; then
    curl -fsSL -o "$dest" "$url"
  else
    python3 -c "import urllib.request; urllib.request.urlretrieve('$url', '$dest')"
  fi
}

for dataset_json in "${DATASET_LINES[@]}"; do
  [[ -z "$dataset_json" ]] && continue

  dtype=$(get_field "$dataset_json" "type")
  path_rel=$(get_field "$dataset_json" "path")
  target_rel=$(get_field "$dataset_json" "target")
  expected_glob=$(get_field "$dataset_json" "expected_glob")

  case "$dtype" in
    local_tar)
      TARGET_DIR="$PROBLEM_DIR/$target_rel"
      mkdir -p "$TARGET_DIR"

      # Check if already present
      if [[ -n "$expected_glob" ]] && compgen -G "$TARGET_DIR/$expected_glob" &>/dev/null; then
        echo "[vdb setup] Dataset already present at $TARGET_DIR"
        continue
      fi

      # Check mounted datasets
      MOUNTED="/datasets/vdb_design"
      if [[ -d "$MOUNTED" ]] && compgen -G "$MOUNTED/*.fvecs" &>/dev/null; then
        echo "[vdb setup] Using pre-downloaded dataset from $MOUNTED"
        ln -sf "$MOUNTED"/* "$TARGET_DIR/"
        continue
      fi

      # Download if needed
      TAR_PATH="$PROBLEM_DIR/$path_rel"
      if [[ ! -f "$TAR_PATH" ]]; then
        echo "[vdb setup] Downloading SIFT1M dataset..."
        download_file "ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz" "$TAR_PATH"
      fi

      # Extract
      echo "[vdb setup] Extracting dataset..."
      TMP_DIR="$PROBLEM_DIR/resources/tmp_sift"
      mkdir -p "$TMP_DIR"
      tar -xzf "$TAR_PATH" -C "$TMP_DIR" 2>/dev/null || true
      for f in sift_base.fvecs sift_learn.fvecs sift_query.fvecs sift_groundtruth.ivecs; do
        find "$TMP_DIR" -name "$f" -exec mv {} "$TARGET_DIR/" \;
      done
      rm -rf "$TMP_DIR"
      ;;
    *)
      echo "Error: Unsupported dataset type: $dtype" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$PROBLEM_DIR/resources/data/index_cache"
echo "[vdb setup] Dataset preparation complete"
