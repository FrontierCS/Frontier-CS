#!/usr/bin/env bash
set -euo pipefail

# Downloads datasets for cant_be_late problem to local datasets folder

PROBLEM_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROBLEM_NAME=$(basename "$PROBLEM_DIR")
BASE_DIR=$(cd "$PROBLEM_DIR/../../.." && pwd)
DATASETS_DIR="$BASE_DIR/datasets/cant_be_late/$PROBLEM_NAME"

mkdir -p "$DATASETS_DIR"

echo "[$PROBLEM_NAME download] Checking for real_traces dataset..."

# Check if dataset already exists
if compgen -G "$DATASETS_DIR/real/ddl=search+task=48+overhead=*/real/*/traces/random_start/*.json" >/dev/null 2>&1; then
  echo "[$PROBLEM_NAME download] Dataset already exists at $DATASETS_DIR"
  exit 0
fi

# Check if tar file exists in problem resources
TAR_PATH="$PROBLEM_DIR/resources/real_traces.tar.gz"

if [[ ! -f "$TAR_PATH" ]]; then
  echo "Error: dataset tarball missing at $TAR_PATH" >&2
  exit 1
fi

# Extract dataset
echo "[$PROBLEM_NAME download] Extracting dataset..."
tar -xzf "$TAR_PATH" -C "$DATASETS_DIR" 2>/dev/null || true

# Verify extraction
if ! compgen -G "$DATASETS_DIR/real/ddl=search+task=48+overhead=*/real/*/traces/random_start/*.json" >/dev/null 2>&1; then
  echo "Error: Expected files not found after extraction" >&2
  exit 1
fi

echo "[$PROBLEM_NAME download] Dataset ready at $DATASETS_DIR"


