#!/usr/bin/env bash
set -euo pipefail

# Copies datasets for llm_router problem to local datasets folder

PROBLEM_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Go up from problem_dir to problems/, then to repo root
BASE_DIR=$(cd "$PROBLEM_DIR/../../.." && pwd)
DATASETS_DIR="$BASE_DIR/datasets/llm_router"

# Create the final destination directory
mkdir -p "$DATASETS_DIR"

echo "[llm_router download] Checking for datasets..."

# Define resource directories
RESOURCES_DIR="$PROBLEM_DIR/resources"
SRC_DATASETS_DIR="$RESOURCES_DIR/datasets"
TARGET_PKL="$SRC_DATASETS_DIR/routerbench_0shot.pkl"
DOWNLOAD_URL="https://huggingface.co/datasets/withmartian/routerbench/resolve/main/routerbench_0shot.pkl"
PREPARE_SCRIPT="$RESOURCES_DIR/prepare_data.py"

# --- 1. Create the local resource directory (datasets repo) ---
# mkdir -p creates parent directories (resources/) if they are missing
if [[ ! -d "$SRC_DATASETS_DIR" ]]; then
  echo "[llm_router download] Creating directory $SRC_DATASETS_DIR..."
  mkdir -p "$SRC_DATASETS_DIR"
fi

# --- 2. Download the pickle file ---
if [[ ! -f "$TARGET_PKL" ]]; then
  echo "[llm_router download] Downloading routerbench_0shot.pkl..."
  if command -v curl &> /dev/null; then
      curl -L "$DOWNLOAD_URL" -o "$TARGET_PKL"
  elif command -v wget &> /dev/null; then
      wget -O "$TARGET_PKL" "$DOWNLOAD_URL"
  else
      echo "Error: Neither curl nor wget found. Cannot download dataset." >&2
      exit 1
  fi
else
  echo "[llm_router download] Pickle file already exists, skipping download."
fi

# --- 3. Trigger the Python processing script ---
if [[ -f "$PREPARE_SCRIPT" ]]; then
    echo "[llm_router download] Running data preparation script..."
    python3 "$PREPARE_SCRIPT"
else
    echo "Error: prepare_data.py not found at $PREPARE_SCRIPT" >&2
    exit 1
fi

# --- 4. Copy all datasets to final location ---
echo "[llm_router download] Copying datasets to final location..."
cp -r "$SRC_DATASETS_DIR"/* "$DATASETS_DIR/"

echo "[llm_router download] Dataset ready at $DATASETS_DIR"