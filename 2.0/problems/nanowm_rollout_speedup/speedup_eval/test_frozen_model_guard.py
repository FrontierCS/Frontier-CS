"""Unit test for the frozen-model guard (speedup temp_embed gray area).

Runs WITHOUT torch (a tiny pure-Python tensor stub) so it is CI-checkable on the
CPU judge; if torch is present it additionally checks a real nn.Module. Verifies:
  1. no mutation                       -> fingerprint unchanged (assert_frozen passes)
  2. persistent value mutation         -> CAUGHT (assert_frozen raises)
  3. transient reshape THEN RESTORE     -> passes (the causal-prefix temp_embed case)
  4. a different-but-sum-preserving... -> documented residual (NOT a goal; quality gate)

Run:  python -m speedup_eval.test_frozen_model_guard   (exit non-zero on regression)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from speedup_eval.frozen_model_guard import model_param_fingerprint, assert_frozen  # noqa: E402


class _Stub:
    """Minimal tensor stub: a value list with .shape/.dtype/.detach()/.sum()."""
    def __init__(self, vals, shape=None, dtype="float32"):
        self.vals = list(vals)
        self.shape = tuple(shape) if shape is not None else (len(self.vals),)
        self.dtype = dtype

    def detach(self):
        return self

    def to(self, *a, **k):
        return self

    def double(self):
        return self

    def sum(self):
        return sum(self.vals)


class _Model:
    def __init__(self, sd):
        self._sd = sd

    def state_dict(self):
        return self._sd


def main() -> int:
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL:", msg); ok = False

    # Build a frozen model and snapshot it.
    sd = {
        "blocks.0.weight": _Stub([0.1, 0.2, 0.3], shape=(3,)),
        "temp_embed": _Stub([1.0, 2.0, 3.0, 4.0], shape=(1, 4, 1)),
        "pos_embed": _Stub([0.5, 0.5], shape=(1, 2, 1)),
    }
    model = _Model(sd)
    fp0 = model_param_fingerprint(model)

    # 1) No mutation -> passes.
    try:
        assert_frozen(model, fp0)
    except RuntimeError:
        check(False, "no-op model wrongly flagged as mutated")

    # 2) Persistent value mutation -> caught.
    sd["blocks.0.weight"] = _Stub([0.1, 0.2, 0.9], shape=(3,))  # changed a value
    caught = False
    try:
        assert_frozen(model, fp0)
    except RuntimeError:
        caught = True
    check(caught, "persistent weight mutation NOT caught")
    sd["blocks.0.weight"] = _Stub([0.1, 0.2, 0.3], shape=(3,))  # restore for next case

    # 3) Transient reshape THEN restore (the causal-prefix temp_embed pattern):
    #    slice temp_embed during the rollout, then put the original back -> passes.
    original = sd["temp_embed"]
    sd["temp_embed"] = _Stub(original.vals[:2], shape=(1, 2, 1))  # sliced prefix (transient)
    # ... (model used on the cropped window here) ...
    sd["temp_embed"] = original                                   # restored in finally
    try:
        assert_frozen(model, fp0)
    except RuntimeError:
        check(False, "restored transient reshape wrongly flagged (would block causal-prefix)")

    # 4) Shape change alone (e.g. left sliced, not restored) -> caught (structure hash).
    sd["temp_embed"] = _Stub(original.vals[:2], shape=(1, 2, 1))
    caught = False
    try:
        assert_frozen(model, fp0)
    except RuntimeError:
        caught = True
    check(caught, "unrestored temp_embed reshape NOT caught")
    sd["temp_embed"] = original

    # Optional: same checks against a real torch nn.Module if torch is installed.
    try:
        import torch  # type: ignore
        import torch.nn as nn  # type: ignore
        m = nn.Linear(4, 4)
        f0 = model_param_fingerprint(m)
        assert_frozen(m, f0)                       # no-op passes
        with torch.no_grad():
            m.weight[0, 0] += 1.0                  # persistent mutation
        hit = False
        try:
            assert_frozen(m, f0)
        except RuntimeError:
            hit = True
        check(hit, "torch nn.Module persistent mutation NOT caught")
        print("torch path: checked a real nn.Linear")
    except ImportError:
        print("torch not installed -> stub-only check (CI path)")

    print("RESULT:", "PASS - frozen-model guard catches persistent mutation, allows restored reshape"
          if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
