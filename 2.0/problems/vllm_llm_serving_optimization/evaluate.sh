#!/usr/bin/env bash
# Local CLI evaluation for vllm_llm_serving_optimization.
#
# Full runs need Modal + Hugging Face credentials (MODAL_TOKEN_ID/SECRET, HF_TOKEN)
# and the baked clean vLLM source + serving_eval harness at /opt (see the judge
# image). Without those the evaluator validates the patch policy and returns a
# smoke score, which is what repository CI exercises (the empty reference patch
# passes). Pass a patch path to score it directly.
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SOLUTION="${1:-$SCRIPT_DIR/reference.patch}"
exec python3 "$SCRIPT_DIR/evaluator.py" "$SOLUTION"
