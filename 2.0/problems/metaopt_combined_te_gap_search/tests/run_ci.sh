#!/usr/bin/env bash
set -euo pipefail
python3 -m unittest -v "$(dirname "$0")/test_harbor_submission.py"
