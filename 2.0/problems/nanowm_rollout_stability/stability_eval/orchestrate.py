"""GPU orchestration for nanowm_rollout_speedup.

`run_pair(patch_path, clips, role)` returns (baseline_metrics, patched_metrics),
each {"gen_seconds", "lpips", "clips", "steps"}.

Two backends, selected automatically:
  - MODAL  (FRONTIER_NWM_BACKEND=modal or a Modal token is present): runs the
    rollout in a Modal GPU sandbox (the maintainer-facing path, mirroring
    vllm_llm_serving_optimization; judge container stays CPU-only).
  - LOCAL  (default when a CUDA device is visible): runs the runner directly on
    the local GPU. Used for Della validation and any GPU-equipped judge.

The unpatched baseline is computed once and cached (baseline_cache_path); the
patched run always re-applies the agent patch to a clean checkout.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import settings as S


def _compose_config() -> Path:
    """Write the fixed CSGO rollout config (subset val list) the runner consumes."""
    out = Path(os.environ.get("FRONTIER_NWM_WORKDIR", "/tmp/nwm_speedup")) / "csgo_config.yaml"
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
    the patch text + config travel into the sandbox, which runs stability_eval.runner
    on the baked NanoWM checkout and returns the metrics dict."""
    from .modal_app import run_rollout_remote  # deploys/looks up the Modal app
    patch_text = "" if patch_path is None else Path(patch_path).read_text(errors="replace")
    return run_rollout_remote(patch_text=patch_text, clips=clips, steps=S.NUM_SAMPLING_STEPS)


def _backend():
    b = os.environ.get("FRONTIER_NWM_BACKEND", "").lower()
    if b in ("modal", "local"):
        return b
    if os.environ.get("MODAL_TOKEN_ID") or os.environ.get("MODAL_TOKEN_SECRET"):
        return "modal"
    return "local"


def _baseline(clips: int, run) -> dict:
    cache = S.BASELINE_CACHE
    if cache.exists():
        try:
            data = json.loads(cache.read_text())
            # Deterministic seeding makes the cached baseline a valid common-random
            # -numbers partner ONLY for the same clip set (== not >=) and same seed.
            if data.get("clips") == clips and data.get("seed") == S.SEED:
                return data
        except Exception:
            pass
    m = run(None, clips)
    m["seed"] = S.SEED
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(m))
    except OSError:
        pass
    return m


def run_pair(patch_path: Path, clips: int, role: str = "agent") -> tuple[dict, dict]:
    run = _run_modal if _backend() == "modal" else _run_local
    baseline = _baseline(clips, run)
    patched = run(Path(patch_path), clips)
    return baseline, patched
