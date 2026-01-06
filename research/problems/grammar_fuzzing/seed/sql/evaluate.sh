#!/usr/bin/env bash
# Don't use set -euo pipefail so we can capture errors
set -e

# evaluate.sh wrapper for grammar_fuzzing/sql_parser
PROBLEM_DIR=$(pwd)
echo "[evaluate] Running grammar_fuzzing/sql_parser evaluation..." >&2
echo "[evaluate] Current dir: $(pwd)" >&2

# Try to run the evaluator, capture output
if ./run_evaluator.sh 2>&1 | tee /tmp/eval_output_grammar_fuzzing_sql_parser.log; then
    echo "[evaluate] run_evaluator succeeded" >&2
else
    echo "[evaluate] ERROR: run_evaluator.sh failed!" >&2
    echo "[evaluate] Output:" >&2
    cat /tmp/eval_output_grammar_fuzzing_sql_parser.log >&2
    echo "-10000"
    exit 0
fi

# Try to read results
if [[ -f "results.json" ]]; then
    echo "[evaluate] Found results.json" >&2
    cat results.json | python3 -c "import json, sys; print(json.load(sys.stdin).get('score', 0.0))"
else
    echo "[evaluate] WARNING: results.json not found, returning error score" >&2
    echo "-10000"
fi


