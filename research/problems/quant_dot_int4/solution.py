"""
Minimal reference submission for quant_dot_int4.

This file is intentionally simple:
- Exposes a `quant_dot(...)` function (baseline PyTorch implementation).
- Implements `Solution.solve()` returning `program_path` pointing to this file.

In the real benchmark environment, users should replace `quant_dot` with an optimized
Triton implementation.
"""

from __future__ import annotations

from pathlib import Path

# The evaluator adds `resources/` to sys.path before importing this program,
# so this import works when evaluated.
from quant_dot_baseline import quant_dot  # noqa: F401


class Solution:
    def solve(self, spec_path: str | None = None) -> dict:
        return {"program_path": str(Path(__file__).resolve())}



