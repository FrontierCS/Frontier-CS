"""GPU orchestration for nanowm_rollout_speedup.

`run_pair(patch_path, clips, role)` returns (baseline_metrics, patched_metrics),
each {"gen_seconds", "lpips", "clips", "steps"}.

Two backends, selected automatically:
  - MODAL  (FRONTIER_NWM_BACKEND=modal or a Modal token is present): runs the
    rollout in a Modal GPU sandbox (the maintainer-facing path, mirroring
    vllm_llm_serving_optimization; judge container stays CPU-only).
  - LOCAL  (default when a CUDA device is visible): runs the runner directly on
    the local GPU. Used for Della validation and any GPU-equipped judge.

Baseline measurement (audit P1, common random numbers):
  - role="final" (the SCORED verifier run): baseline and patched are measured
    back-to-back on ONE GPU in one job (no cache). They run as two separate
    rollout subprocesses (not one process), so what makes a no-op score ~0 is
    op-level bit-stability -- the determinism flags in rollout.py/evaluate_metrics.py
    holding for EVERY op, plus the per-clip seed. Pairing removes cross-run,
    cross-container, cross-cache and cross-hardware variance; it does NOT by
    itself cancel op-level nondeterminism. Prove the flags actually hold once on
    H100 with FRONTIER_NWM_STRICT_DETERMINISM=1 (a fallback then raises).
  - role="agent" (cheap iterative feedback): the unpatched baseline is cached,
    keyed by a full config fingerprint; deterministic kernels + per-clip seeding
    keep that cached baseline a valid CRN partner on the fixed (now H100) SKU.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import settings as S


def _compose_config() -> Path:
    """Write the fixed CSGO rollout config (subset val list) the runner consumes.

    The filename carries the config fingerprint so a changed task config never
    silently reuses a stale composed config from a long-lived container."""
    workdir = Path(os.environ.get("FRONTIER_NWM_WORKDIR", "/tmp/nwm_speedup"))
    out = workdir / f"csgo_config_{S.config_fingerprint()}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return out
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf
    with initialize_config_dir(config_dir=str(S.REPO / "src/configs"), version_base=None):
        cfg = compose(config_name="config", overrides=[
            f"model={S.MODEL}", f"dataset={S.DATASET}", "experiment=evaluate_only",
            "wandb.enabled=false",
            f"dataset.loader.val_file_list={S.VAL_FILES}",
            f"dataset.loader.train_file_list={S.VAL_FILES}",
            f"dataset.loader.val_start_indices={S.VAL_STARTS}",
        ])
    out.write_text(OmegaConf.to_yaml(cfg, resolve=False))
    return out


def _run_local(patch_path: Path | None, clips: int) -> dict:
    from . import runner
    return runner.evaluate(S.REPO, patch_path, _compose_config(), S.CKPT,
                           clips=clips, steps=S.NUM_SAMPLING_STEPS, device="cuda")


def _run_modal(patch_path: Path | None, clips: int) -> dict:
    """Run one rollout inside a Modal GPU sandbox. Mirrors #145's modal_app:
    the patch text + config travel into the sandbox, which runs speedup_eval.runner
    on the baked NanoWM checkout and returns the metrics dict."""
    from .modal_app import run_rollout_remote  # deploys/looks up the Modal app
    patch_text = "" if patch_path is None else Path(patch_path).read_text(errors="replace")
    return run_rollout_remote(patch_text=patch_text, clips=clips, steps=S.NUM_SAMPLING_STEPS,
                              strict=S.STRICT_DETERMINISM)


def _run_pair_local(patch_path: Path, clips: int) -> tuple[dict, dict]:
    """Baseline then patched, back-to-back on the same local GPU (two rollout
    subprocesses; op-level determinism is what makes them comparable)."""
    import tempfile
    from . import runner
    cfg = _compose_config()
    base_dir = tempfile.mkdtemp(prefix="nwm_faith_base_")
    patch_dir = tempfile.mkdtemp(prefix="nwm_faith_patch_")
    baseline = runner.evaluate(S.REPO, None, cfg, S.CKPT, clips=clips,
                               steps=S.NUM_SAMPLING_STEPS, device="cuda", keep_gen=base_dir)
    patched = runner.evaluate(S.REPO, Path(patch_path), cfg, S.CKPT, clips=clips,
                              steps=S.NUM_SAMPLING_STEPS, device="cuda", keep_gen=patch_dir)
    try:  # (A) faithfulness of the patched rollout to the baseline rollout
        patched["faithfulness_lpips"] = runner.frames_lpips(Path(base_dir), Path(patch_dir), "cuda")
    except Exception:
        patched["faithfulness_lpips"] = None
    return baseline, patched


def _run_pair_modal(patch_path: Path, clips: int) -> tuple[dict, dict]:
    """Baseline + patched in ONE Modal GPU container (true CRN pair)."""
    from .modal_app import run_pair_remote
    patch_text = Path(patch_path).read_text(errors="replace")
    res = run_pair_remote(patch_text=patch_text, clips=clips, steps=S.NUM_SAMPLING_STEPS,
                          strict=S.STRICT_DETERMINISM)
    return res["baseline"], res["patched"]


def _backend():
    b = os.environ.get("FRONTIER_NWM_BACKEND", "").lower()
    if b in ("modal", "local"):
        return b
    if os.environ.get("MODAL_TOKEN_ID") or os.environ.get("MODAL_TOKEN_SECRET"):
        return "modal"
    return "local"


def _baseline(clips: int, run) -> dict:
    cache = S.BASELINE_CACHE
    fp = S.config_fingerprint()
    if cache.exists():
        try:
            data = json.loads(cache.read_text())
            # Valid cached CRN partner only for the IDENTICAL config (fingerprint
            # covers model/dataset/rollout/steps/scheduling/stab/batch/seed/val set)
            # and the same clip count; deterministic kernels keep it bit-stable.
            if data.get("fingerprint") == fp and data.get("clips") == clips:
                return data
        except Exception:
            pass
    m = run(None, clips)
    m["seed"] = S.SEED
    m["fingerprint"] = fp
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(m))
    except OSError:
        pass
    return m


def run_pair(patch_path: Path, clips: int, role: str = "agent") -> tuple[dict, dict]:
    backend = _backend()
    if role == "final":
        # Scored run: baseline and patched measured back-to-back on one GPU in one
        # job (no cache). Removes cross-run/-container/-cache/-hardware variance;
        # the no-op->0 guarantee additionally needs the determinism flags to hold
        # for every op (prove once on H100 with FRONTIER_NWM_STRICT_DETERMINISM=1).
        if backend == "modal":
            return _run_pair_modal(Path(patch_path), clips)
        return _run_pair_local(Path(patch_path), clips)
    # Iterative (agent) feedback: cached baseline for speed; determinism + seeding
    # keep it a valid CRN partner on the fixed GPU SKU.
    run = _run_modal if backend == "modal" else _run_local
    baseline = _baseline(clips, run)
    patched = run(Path(patch_path), clips)
    return baseline, patched
