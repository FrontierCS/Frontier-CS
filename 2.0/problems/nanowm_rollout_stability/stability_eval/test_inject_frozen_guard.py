"""Test runner.inject_frozen_guard: it must place a working frozen-model guard into
a copied rollout.py (snapshot after model.eval(), verify before the final print),
catch a persistent model mutation, allow a restored transient reshape (causal-prefix),
fail CLOSED when anchors are missing, and be idempotent. Runs without torch/GPU by
injecting into a synthetic rollout.py with a fake torch + stub model and exec-ing it.

Run:  python -m stability_eval.test_inject_frozen_guard   (exit non-zero on regression)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from stability_eval import runner  # noqa: E402


# A synthetic rollout.py: the loaded `model` is eval'd, the SAMPLER runs (and may
# mutate the model), then the final "Done!" print. {SAMPLER} is filled per-case.
SYNTH = '''
import torch
def main():
    model = MODEL
    model.eval()
    for _b in range(2):
        SAMPLER(model)
    print(f"Done! Processed {{N}} samples.")
main()
'''


class _Stub:
    def __init__(self, vals, shape=None, dtype="float32"):
        self.vals = list(vals); self.shape = tuple(shape or (len(self.vals),)); self.dtype = dtype
    def detach(self): return self
    def to(self, *a, **k): return self
    def sum(self): return sum(self.vals)


class _Model:
    def __init__(self): self._sd = {"w": _Stub([0.1, 0.2, 0.3]), "temp_embed": _Stub([1.0, 2.0, 3.0, 4.0], (1, 4, 1))}
    def state_dict(self): return self._sd
    def eval(self): return self


class _FakeTorch:
    float64 = "float64"


def _write_synth(tmp: Path) -> Path:
    f = tmp / "src" / "sample" / "rollout.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(SYNTH)
    return f


def _run_injected(repo: Path, sampler) -> tuple[bool, str]:
    """Inject, then exec the resulting rollout.py with a fake torch/model/sampler.
    Returns (raised, message)."""
    runner.inject_frozen_guard(repo)
    src = (repo / "src" / "sample" / "rollout.py").read_text()
    compile(src, "rollout.py", "exec")  # syntactic validity
    g = {"MODEL": _Model(), "SAMPLER": sampler, "N": 2, "torch": _FakeTorch(),
         "print": lambda *a, **k: None}
    # shadow `import torch` inside the synthetic module with our fake
    sys.modules.setdefault("torch", _FakeTorch())
    try:
        exec(compile(src, "rollout.py", "exec"), g)
        return False, "ok"
    except RuntimeError as e:
        return True, str(e)


def main() -> int:
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL:", msg); ok = False

    # 1) no-op sampler -> guard passes (no raise).
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d); _write_synth(repo)
        raised, msg = _run_injected(repo, lambda m: None)
        check(not raised, f"no-op rollout wrongly flagged: {msg}")

    # 2) restored transient reshape (causal-prefix temp_embed) -> passes.
    def transient(m):
        sd = m.state_dict(); orig = sd["temp_embed"]
        sd["temp_embed"] = _Stub(orig.vals[:2], (1, 2, 1))  # sliced during forward
        sd["temp_embed"] = orig                             # restored in finally
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d); _write_synth(repo)
        raised, msg = _run_injected(repo, transient)
        check(not raised, f"restored transient reshape wrongly flagged (blocks causal-prefix): {msg}")

    # 3) persistent mutation -> CAUGHT (raise).
    def persistent(m):
        m.state_dict()["w"] = _Stub([0.1, 0.2, 0.9])  # never restored
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d); _write_synth(repo)
        raised, msg = _run_injected(repo, persistent)
        check(raised and "frozen-model violation" in msg, f"persistent mutation NOT caught: {msg}")

    # 4) idempotent: a second injection does not double-insert.
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d); f = _write_synth(repo)
        runner.inject_frozen_guard(repo)
        once = f.read_text()
        runner.inject_frozen_guard(repo)
        check(f.read_text() == once and once.count("_fg_frozen = _fg_fp(model)") == 1, "injection not idempotent")

    # 5) FAIL CLOSED: missing anchor (no model.eval()) -> raise, do not run unguarded.
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d); f = _write_synth(repo)
        f.write_text('def main():\n    x = 1\n    print(f"Done! Processed 0 samples.")\nmain()\n')
        caught = False
        try:
            runner.inject_frozen_guard(repo)
        except RuntimeError as e:
            caught = "anchors not found" in str(e)
        check(caught, "missing-anchor injection did NOT fail closed")

    print("RESULT:", "PASS - frozen guard injects, catches persistent mutation, allows "
          "restored reshape, fails closed" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
