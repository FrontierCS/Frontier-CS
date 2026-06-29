"""vLLM serving evaluation harness (shared by the judge and the public test).

Public API:
    run_measurement(...)  -> dict   # judge-side: baseline vs patched, gated
    run_public_test(...)  -> dict   # agent-side: serve working tree, feedback
"""

from __future__ import annotations

from .measure import run_measurement, run_public_test

__all__ = ["run_measurement", "run_public_test"]
__version__ = "0.1.0"
