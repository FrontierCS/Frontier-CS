"""Modal GPU evaluation harness for the flashlib kernel-optimization task family.

Shared by the judge (evaluator.py) and the agent public test. Baked into both
the agent and judge images at ``/opt/flash_gpu.py``. It runs a frozen naive
baseline and the (patched or agent-edited) package on a Modal GPU and returns
per-workload timings + quality verdicts.

Anti-reward-hack properties (all enforced inside the remote worker, which is the
only place the untrusted code runs):

* **Timing primitives are captured before any agent code is imported** — the
  worker binds ``time.perf_counter`` and ``torch.cuda.synchronize`` to locals up
  front, so a submission that monkey-patches ``torch.cuda.synchronize`` (or any
  torch attribute) cannot affect measurement.
* **Fresh data every timed iteration** — each measured iteration generates a new
  input from a fresh seed, so a submission cannot memoize on a repeated input.
* **Quality is verified on every timed iteration** — the judge recomputes the
  quality metric from the *returned tensors* on that iteration's data and gates
  it, so returning a stale cached result for a different input is caught.
* **The judge computes all metrics** — no agent-provided number is trusted.
* **Fresh container per submission** — an ephemeral Modal app is used, so no
  global state survives across evaluations.

The remote worker is a single self-contained function serialized to Modal
(``serialized=True``), so the remote does not import this module and there is no
module-mounting to get wrong. The GPU image ships torch + triton (+ any extra
pip packages a task needs for its reference build).
"""
from __future__ import annotations

import os


# --------------------------------------------------------------------------- #
# Remote worker (runs on the Modal GPU). Fully self-contained: every helper is
# nested so cloudpickle ships the whole thing. Takes and returns plain data.
# --------------------------------------------------------------------------- #
def _gpu_worker(payload: dict) -> dict:
    import importlib
    import os as _os
    import sys as _sys
    import tempfile
    import time
    import traceback

    import torch

    # Capture timing + sync references BEFORE importing any submission code, so a
    # monkey-patch of torch.cuda.synchronize cannot affect measurement.
    _perf = time.perf_counter
    _sync = torch.cuda.synchronize
    if not torch.cuda.is_available():
        return {"ok": False, "error": "cuda_unavailable"}
    dev = "cuda"

    cfg = payload["cfg"]
    prim = cfg["primitive"]
    warmup = int(cfg.get("warmup", 3))
    iters = int(cfg.get("iters", 7))

    def _materialize(files: dict, tag: str) -> str:
        root = tempfile.mkdtemp(prefix=f"flash_{tag}_")
        for rel, content in files.items():
            path = _os.path.join(root, rel)
            parent = _os.path.dirname(path)
            if parent:
                _os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        _sys.path.insert(0, root)
        return root

    _materialize(payload["baseline_files"], "baseline")
    _materialize(payload["patched_files"], "patched")
    ref = importlib.import_module(cfg["ref_module"])
    pkg = importlib.import_module(cfg["pkg"])

    # ---- per-primitive: data gen, call, and quality metric ---------------- #
    def gen(w, seed):
        g = torch.Generator(device=dev).manual_seed(int(seed))
        if prim == "knn":
            db = torch.randn(w["M"], w["D"], generator=g, device=dev, dtype=torch.float32)
            q = torch.randn(w["Q"], w["D"], generator=g, device=dev, dtype=torch.float32)
            return {"queries": q, "database": db}
        x = torch.randn(w["N"], w["D"], generator=g, device=dev, dtype=torch.float32)
        if prim == "kmeans":
            perm = torch.randperm(w["N"], generator=g, device=dev)[: w["K"]]
            return {"x": x, "init": x.index_select(0, perm).clone()}
        return {"x": x}

    def call(mod, w, data):
        if prim == "kmeans":
            return mod.kmeans(data["x"], w["K"], max_iters=w["max_iters"],
                              init_centroids=data["init"], tol=0.0)
        if prim == "knn":
            return mod.knn(data["queries"], data["database"], w["k"])
        if prim == "pca":
            return mod.pca(data["x"], w["k"])
        if prim == "tsvd":
            return mod.truncated_svd(data["x"], w["k"])
        raise ValueError(prim)

    def check_shape(w, out):
        if prim == "kmeans":
            _, cen, _ = out
            if tuple(cen.shape) != (w["K"], w["D"]) or not torch.isfinite(cen).all():
                raise ValueError("bad kmeans output")
        elif prim == "knn":
            d, i = out
            if tuple(d.shape) != (w["Q"], w["k"]) or tuple(i.shape) != (w["Q"], w["k"]):
                raise ValueError("bad knn output")
            if not torch.isfinite(d).all():
                raise ValueError("non-finite distances")
        else:
            a, b = out
            comps = a if prim == "pca" else b
            if tuple(comps.shape) != (w["k"], w["D"]) or not torch.isfinite(comps).all():
                raise ValueError("bad decomposition output")

    def inertia(x, centroids):
        c = centroids.to(torch.float32)
        cn = (c * c).sum(1)
        total = 0.0
        for j in range(0, x.shape[0], 16384):
            xb = x[j:j + 16384]
            d = (xb * xb).sum(1, keepdim=True) - 2.0 * (xb @ c.t()) + cn[None, :]
            total += float(d.min(1).values.clamp_min(0).sum().item())
        return total

    def recall(agent_idx, ref_idx):
        a = agent_idx.long(); b = ref_idx.long()
        hit = (a.unsqueeze(2) == b.unsqueeze(1)).any(2)
        return float(hit.sum().item()) / (b.shape[0] * b.shape[1])

    def ortho_err(comps):
        c = comps.to(torch.float32); k = c.shape[0]
        return float((c @ c.t() - torch.eye(k, device=c.device)).abs().max().item())

    def captured(x, comps, center):
        c = comps.to(torch.float32)
        mean = x.mean(0) if center else None
        total = 0.0
        for j in range(0, x.shape[0], 16384):
            xb = x[j:j + 16384]
            if center:
                xb = xb - mean
            p = xb @ c.t()
            total += float((p * p).sum().item())
        return total / (x.shape[0] - 1) if center else total

    def verdict(w, data, ref_out, agent_out):
        """Return (ok, reason, ref_val, agent_val) gating the agent output."""
        check_shape(w, agent_out)
        if prim == "kmeans":
            rv = inertia(data["x"], ref_out[1]); av = inertia(data["x"], agent_out[1])
            tol = float(cfg["inertia_tolerance"])
            ok = av <= (1.0 + tol) * rv + 1e-6
            return ok, ("inertia_regression" if not ok else ""), rv, av
        if prim == "knn":
            rec = recall(agent_out[1], ref_out[1])
            ok = rec >= float(cfg["recall_threshold"])
            return ok, ("recall_regression" if not ok else ""), 1.0, rec
        center = (prim == "pca")
        comps = agent_out[0] if prim == "pca" else agent_out[1]
        ref_comps = ref_out[0] if prim == "pca" else ref_out[1]
        oe = ortho_err(comps)
        if oe > float(cfg["ortho_tolerance"]):
            return False, "not_orthonormal", 0.0, oe
        rv = captured(data["x"], ref_comps, center)
        av = captured(data["x"], comps, center)
        ok = av >= (1.0 - float(cfg["captured_tolerance"])) * rv - 1e-6
        return ok, ("captured_regression" if not ok else ""), rv, av

    def time_call(mod, w, data):
        _sync(); t0 = _perf(); out = call(mod, w, data); _sync()
        return (_perf() - t0) * 1000.0, out

    rows = []
    try:
        for w in payload["workloads"]:
            base_seed = int(w["seed"])
            # warmup on fresh data (kernels / autotune) — not measured
            for i in range(warmup):
                d = gen(w, base_seed + 100 + i)
                call(ref, w, d); call(pkg, w, d); _sync()
                del d
            torch.cuda.empty_cache()
            ratios, ref_val, agent_val = [], None, None
            bad = None
            for i in range(iters):
                d = gen(w, base_seed + 10000 + i)          # fresh every iteration
                rt, rout = time_call(ref, w, d)
                at, aout = time_call(pkg, w, d)
                ok, reason, rv, av = verdict(w, d, rout, aout)   # verify THIS iter
                if not ok:
                    bad = reason; ref_val, agent_val = rv, av
                    break
                ratios.append(rt / at if at > 0 else 0.01)
                ref_val, agent_val = rv, av
                del d, rout, aout
                torch.cuda.empty_cache()
            if bad is not None:
                rows.append({"id": w["id"], "ok": False, "reason": bad,
                             "ref_val": ref_val, "agent_val": agent_val})
                continue
            ratios.sort()
            rows.append({"id": w["id"], "ok": True,
                         "speedup": ratios[len(ratios) // 2],
                         "ref_val": ref_val, "agent_val": agent_val})
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                "trace": traceback.format_exc()[-500:]}
    return {"ok": True, "rows": rows}


# --------------------------------------------------------------------------- #
# Host-side wrappers (run in the judge / agent container; need MODAL tokens).
# --------------------------------------------------------------------------- #
def _build_image(cfg: dict):
    import modal
    pip = list(cfg.get("pip", ["torch==2.5.1", "triton==3.1.0", "numpy"]))
    base = cfg.get("cuda_image", "nvidia/cuda:12.4.1-devel-ubuntu22.04")
    # add_python must match the judge/agent container Python (ubuntu:24.04 -> 3.12)
    # because the worker ships via serialized=True (cloudpickle is version-sensitive).
    # add_local_python_source mounts THIS module into the image so the remote can
    # import it when deserializing the (module-level) worker function.
    return (modal.Image.from_registry(base, add_python=str(cfg.get("python", "3.12")))
            .entrypoint([])
            .pip_install(*pip)
            .add_local_python_source("flash_gpu"))


# Substrings that mark a transient Modal control-plane / image-build failure
# (evicted build, gateway hiccup, app stopped mid-run) rather than a real error
# in the submission — safe to retry.
_TRANSIENT_MARKERS = (
    "external shut-down", "terminated due to external", "please try again",
    "app_state_stopped", "conflicterror", "deadline exceeded", "connection reset",
    "502 bad gateway", "503 service", "temporarily unavailable", "timed out",
    "gateway", "eviction", "internalfailure", "internalerror",
    "failed to get new inputs", "runner failed", "task exited",
)


def _is_transient(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _TRANSIENT_MARKERS)


def run_remote(payload: dict) -> dict:
    """Run the GPU worker on Modal and return its result dict.

    Retries transient Modal control-plane failures; a real error in the
    submission is non-transient and surfaces immediately. Raises RuntimeError
    with a sanitized message on unrecoverable failure.
    """
    import time as _time

    import modal

    cfg = payload["cfg"]
    attempts = max(1, int(cfg.get("modal_retries", 3)))
    last = "modal_gpu_eval_failed"
    for attempt in range(1, attempts + 1):
        app = modal.App(cfg.get("app_name", "flash-kernel-eval"))
        remote = app.function(
            gpu=cfg.get("gpu", "H100"),
            image=_build_image(cfg),
            timeout=int(cfg.get("modal_timeout_seconds", 1800)),
            serialized=True,
            max_containers=1,
        )(_gpu_worker)
        try:
            with modal.enable_output(), app.run():
                return remote.remote(payload)
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[-400:]
            if not _is_transient(last) or attempt == attempts:
                raise RuntimeError(f"modal_gpu_eval_failed: {last}") from exc
            _time.sleep(min(45, 10 * attempt))
    raise RuntimeError(f"modal_gpu_eval_failed: {last}")


def modal_available() -> bool:
    return bool(os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"))
