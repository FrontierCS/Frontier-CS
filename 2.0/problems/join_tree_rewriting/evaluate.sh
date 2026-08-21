#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/solution.patch" >&2
  exit 2
fi
exec python3 "$SCRIPT_DIR/evaluator.py" "$1"
