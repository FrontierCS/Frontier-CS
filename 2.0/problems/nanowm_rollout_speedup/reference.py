"""CI/local reference entry for nanowm_rollout_speedup.

The real reference solution is `reference.patch` (a bf16-autocast sampling
speedup). The Frontier-CS 2.0 CLI's default `evaluator.py <reference.py>` path
expects a Python file; this shim points the evaluator at reference.patch so the
standard `frontier eval` validation works. In smoke/no-GPU mode the evaluator
validates the patch policy and returns a passing score.
"""
import sys
from pathlib import Path

REFERENCE_PATCH = str(Path(__file__).resolve().parent / "reference.patch")

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import json
    from evaluator import evaluate
    s, u, m, mt = evaluate(REFERENCE_PATCH)
    print(json.dumps({"score": s, "score_unbounded": u, "message": m, "metrics": mt}, indent=2))
    print(s)
