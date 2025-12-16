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

# Parse config: first line uv_project (may be empty), subsequent lines dataset JSON objects.
CONFIG_LINES=()
while IFS= read -r line; do
    CONFIG_LINES+=("$line")
done < <(python3 - <<'PY' "$CONFIG_PATH"
import json, sys
from pathlib import Path
cfg_path = Path(sys.argv[1])
try:
    data = json.load(cfg_path.open())
except json.JSONDecodeError as e:
    raise SystemExit(f"Failed to parse {cfg_path}: {e}")
print(data.get("dependencies", {}).get("uv_project", ""))
for dataset in data.get("datasets", []):
    print(json.dumps(dataset))
PY
)

UV_PROJECT_REL="${CONFIG_LINES[0]}"
DATASET_LINES=("${CONFIG_LINES[@]:1}")

# Install uv if not present
if ! command -v uv >/dev/null 2>&1; then
  echo "[vdb_design setup] Installing uv..."
  pip install --user uv || exit 1
  export PATH="$HOME/.local/bin:$PATH"
fi

# Create venv with uv
VENV_DIR="$EXEC_ROOT/.venv"
echo "[vdb_design setup] Creating venv at $VENV_DIR"
uv venv "$VENV_DIR"
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

# Sync uv project dependencies
if [[ -n "$UV_PROJECT_REL" ]]; then
  UV_PROJECT_PATH="$PROBLEM_DIR/$UV_PROJECT_REL"
  if [[ ! -f "$UV_PROJECT_PATH/pyproject.toml" ]]; then
    echo "Error: uv project path $UV_PROJECT_PATH missing pyproject.toml" >&2
    exit 1
  fi
  echo "[vdb_design setup] Syncing dependencies: uv --project $UV_PROJECT_PATH sync"
  uv --project "$UV_PROJECT_PATH" sync --active
else
  echo "[vdb_design setup] No uv_project specified; installing manually"
  uv pip install "numpy>=1.24" "matplotlib>=3.8" "faiss-cpu>=1.7.4"
fi

# Helper: extract field from JSON
get_field() {
  local json="$1"
  local key="$2"
  python3 -c "import json, sys; print(json.loads(sys.argv[1]).get(sys.argv[2], ''))" "$json" "$key"
}

download_file() {
  local url="$1"
  local destination="$2"
  if [[ "${VDB_FORCE_PYTHON_DOWNLOAD:-0}" != "1" ]]; then
    if command -v wget >/dev/null 2>&1; then
      wget -O "$destination" "$url"
      return
    elif command -v curl >/dev/null 2>&1; then
      if [[ "$url" == ftp://* ]]; then
        curl --ftp-method nocwd --fail --location --silent --show-error -o "$destination" "$url"
      else
        curl --fail --location --silent --show-error -o "$destination" "$url"
      fi
      return
    fi
  fi

  python3 - "$url" "$destination" <<'PY'
import sys
from pathlib import Path
from urllib.parse import urlparse

url, destination = sys.argv[1], sys.argv[2]
parsed = urlparse(url)
if parsed.scheme == "ftp":
    from ftplib import FTP

    target_dir = Path(destination).resolve().parent
    target_dir.mkdir(parents=True, exist_ok=True)
    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts:
        raise SystemExit("download failed: empty FTP path")
    *dirs, filename = path_parts
    if not filename:
        raise SystemExit("download failed: FTP path missing filename")
    try:
        with FTP(parsed.hostname, timeout=120) as ftp:
            ftp.login(user="anonymous", passwd="anonymous@")
            ftp.set_pasv(True)
            ftp.voidcmd("TYPE I")
            full_path = "/".join(path_parts)
            if not full_path.startswith("/"):
                full_path = f"/{full_path}"
            try:
                with open(destination, "wb") as out_file:
                    ftp.retrbinary(f"RETR {full_path}", out_file.write)
            except Exception as exc:
                if not dirs:
                    raise
                dir_path = "/".join(dirs)
                if not dir_path.startswith("/"):
                    dir_path = f"/{dir_path}"
                print(f"[vdb_design setup] python FTP fallback retry via cwd -> {dir_path}", file=sys.stderr)
                ftp.cwd(dir_path)
                with open(destination, "wb") as out_file:
                    ftp.retrbinary(f"RETR {filename}", out_file.write)
    except Exception as exc:
        raise SystemExit(f"download failed: {exc}")
else:
    import urllib.request

    try:
        with urllib.request.urlopen(url) as response, open(destination, "wb") as out_file:
            out_file.write(response.read())
    except Exception as exc:
        raise SystemExit(f"download failed: {exc}")
PY
}

# Process datasets
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
      
      # Check if already extracted
      has_data=false
      if [[ -n "$expected_glob" ]]; then
        if compgen -G "$TARGET_DIR/$expected_glob" >/dev/null 2>&1; then
          has_data=true
        fi
      elif [[ -n $(ls -A "$TARGET_DIR" 2>/dev/null) ]]; then
        has_data=true
      fi
      
      if $has_data; then
        echo "[vdb_design setup] Dataset already present at $TARGET_DIR"
        continue
      fi
      
      # Check if dataset is available in mounted /datasets folder
      MOUNTED_DATASETS="/datasets/vdb_design"
      if [[ -d "$MOUNTED_DATASETS" ]] && compgen -G "$MOUNTED_DATASETS/*.fvecs" >/dev/null 2>&1; then
        echo "[vdb_design setup] Using pre-downloaded dataset from $MOUNTED_DATASETS"
        # Create symlinks to mounted datasets instead of copying
        for f in "$MOUNTED_DATASETS"/*; do
          if [[ -f "$f" ]]; then
            ln -sf "$f" "$TARGET_DIR/$(basename "$f")"
          fi
        done
        continue
      fi
      
      if [[ ! -f "$TAR_PATH" ]]; then
        echo "[vdb_design setup] Downloading SIFT1M dataset..."
        echo "TAR_PATH: $TAR_PATH"
        download_file ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz "$TAR_PATH" || {
          echo "[vdb_design setup] Error: Failed to download SIFT1M dataset" >&2
          exit 1
        }
      fi
      
      echo "[vdb_design setup] Extracting $TAR_PATH → $TARGET_DIR"
      TMP_DIR="$PROBLEM_DIR/resources/tmp_sift"
      mkdir -p "$TMP_DIR"
      tar -xzf "$TAR_PATH" -C "$TMP_DIR" 2>/dev/null || true
      
      # Move required files to target directory
      for f in sift_base.fvecs sift_learn.fvecs sift_query.fvecs sift_groundtruth.ivecs; do
        find "$TMP_DIR" -type f -name "$f" -exec mv -f {} "$TARGET_DIR/" \;
      done
      
      rm -rf "$TMP_DIR"
      
      if [[ -n "$expected_glob" ]] && ! compgen -G "$TARGET_DIR/$expected_glob" >/dev/null 2>&1; then
        echo "Error: Expected files $TARGET_DIR/$expected_glob not found after extraction" >&2
        exit 1
      fi
      ;;
    *)
      echo "Error: Unsupported dataset type: $dtype" >&2
      exit 1
      ;;
  esac
done

# Create index cache directory
mkdir -p "$PROBLEM_DIR/resources/data/index_cache"

echo "[vdb_design setup] Environment setup completed successfully"
