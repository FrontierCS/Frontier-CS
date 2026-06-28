"""Frozen-model guard for the speedup judge (audit: temp_embed gray area).

WHY. The agent's allowed scope is `src/diffusion/**` (the sampler), and the model
(`src/models/**`) is FROZEN. The reference-class causal-prefix optimization (codex's
2.87x) reaches into the model from the sampler at RUNTIME -- it temporarily reshapes
`module.temp_embed` (a frozen-tree nn.Parameter) to run the unmodified forward on a
shorter causal window, then RESTORES it via try/finally. That specific use is exact
and benign, and the static patch policy (path allowlist + token scan) cannot see a
runtime attribute monkeypatch. The gray area: nothing stops a DIFFERENT patch from
*persistently* mutating the frozen model (e.g. swapping in blurred/distilled weights
to win wall-clock) from inside the allowed sampler.

WHAT THIS DOES. A cheap dynamic invariant -- "the model you were handed is the model
you must return." Fingerprint the model parameters right after load, re-check after
the rollout. A patch that restores any transient reshape (like causal-prefix) passes;
a patch that leaves the model mutated is a frozen-model violation -> hard error (the
runner attributes a rollout crash to the submission -> score 0). This does NOT catch a
transient swap that is restored before the check -- that residual is covered by the
LPIPS-vs-GT quality guardrail (a degrade trips it) and is documented in DESIGN/AUDIT.

The fingerprint is a structure hash (name/shape/dtype) plus a float64 sum per tensor:
cheap (one reduction per param, OUTSIDE the timed sampling region) and catches any
value change with overwhelming probability. It is not meant to resist an adversary
crafting a sum-preserving mutation -- that is the quality/faithfulness guardrail's job.

WIRING (ACTIVE). `speedup_eval.runner.inject_frozen_guard()` inlines this exact logic
into the copied `src/sample/rollout.py` at apply-time (after the agent patch; rollout.py
is denied to the agent) -- snapshot after `model.eval()`, verify before the final
`print("Done!...")`. So the guard runs on every rollout in BOTH backends WITHOUT
importing this module into the frozen subprocess; this file is the unit-tested
reference (test_frozen_model_guard.py) and the human-readable spec. Injection itself is
fail-closed (raises if rollout.py anchors are missing) and tested in
test_inject_frozen_guard.py. The stability task wires the identical guard in
stability_eval.runner.

Self-contained inline equivalent (what the runner injects):

    import hashlib as _hl
    def _fp(m):
        h=_hl.sha256()
        for n,p in sorted(m.state_dict().items()):
            h.update(f"{n}|{tuple(p.shape)}|{p.dtype}".encode())
            h.update(repr(float(p.detach().to('cpu',dtype=__import__('torch').float64).sum())).encode())
        return h.hexdigest()
"""
from __future__ import annotations

import hashlib


def model_param_fingerprint(model) -> str:
    """SHA-256 over (name, shape, dtype, float64 sum) of every state_dict tensor.

    Works with any object exposing `.state_dict()` returning a name->tensor mapping
    where each tensor has `.shape`, `.dtype`, and `.detach()/.to()/.sum()` (a real
    torch model; a stub in tests). Order-independent (sorted by name)."""
    h = hashlib.sha256()
    for name, p in sorted(model.state_dict().items()):
        h.update(f"{name}|{tuple(p.shape)}|{p.dtype}".encode())
        h.update(repr(_tensor_checksum(p)).encode())
    return h.hexdigest()


def _tensor_checksum(p) -> float:
    """float64 sum of a tensor's values (cheap, catches value changes). Falls back
    through a couple of access paths so it works on real torch tensors and stubs."""
    q = p.detach() if hasattr(p, "detach") else p
    # Prefer a float64 reduction on CPU for cross-device/dtype stability.
    try:
        import torch  # type: ignore
        return float(q.to("cpu", dtype=torch.float64).sum())
    except Exception:
        pass
    try:
        return float(q.double().sum())
    except Exception:
        return float(q.sum())


def assert_frozen(model, fingerprint0: str, where: str = "rollout") -> None:
    """Raise if `model`'s parameters changed since `fingerprint0` was taken."""
    fp = model_param_fingerprint(model)
    if fp != fingerprint0:
        raise RuntimeError(
            f"frozen-model violation: the sampling patch persistently mutated the "
            f"model parameters ({where}); the model is frozen (denied)."
        )
