"""Task settings for nanowm_rollout_speedup, overridable via config.yaml
`evaluation` block (read by the judge) or env vars (local runs)."""
from __future__ import annotations

import json
import os
from pathlib import Path

TASK_CONFIG_PATH = Path(os.environ.get("FRONTIER_NWM_TASK_CONFIG", "/judge/task_config.json"))


def _eval_cfg() -> dict:
    try:
        return (json.loads(TASK_CONFIG_PATH.read_text()).get("evaluation", {}) or {})
    except Exception:
        return {}


_CFG = _eval_cfg()


def _get(name: str, default):
    if name in os.environ:
        v = os.environ[name]
        try:
            return type(default)(v)
        except Exception:
            return v
    return _CFG.get(name.lower().replace("frontier_nwm_", ""), default)


# Domain / model
MODEL = _get("FRONTIER_NWM_MODEL", "nanowm_l2_csgo")
DATASET = _get("FRONTIER_NWM_DATASET", "game/csgo")
# Rollout protocol. LONG rollout (80 frames) so error accumulates into a
# drifted tail; FIXED steps + wall-clock budget (the agent improves the rollout
# PROCEDURE at iso-compute, not by adding steps).
ROLLOUT_LENGTH = int(_get("FRONTIER_NWM_ROLLOUT_LENGTH", 80))
HISTORY_LENGTH = int(_get("FRONTIER_NWM_HISTORY_LENGTH", 4))
NUM_SAMPLING_STEPS = int(_get("FRONTIER_NWM_NUM_STEPS", 50))   # fixed compute budget
SCHEDULING_MODE = _get("FRONTIER_NWM_SCHEDULING", "sequential")
HISTORY_STAB = float(_get("FRONTIER_NWM_HISTORY_STAB", 0.02))  # baseline default
# Drift metric: mean LPIPS over the drifted tail (frames >= this index).
DRIFT_TAIL_START = int(_get("FRONTIER_NWM_DRIFT_TAIL_START", 60))
# Eval set sizes — drift reductions are small, so enough clips to resolve them
# above per-clip noise (validated: 22 clips gives t~2.5 for the reference).
QUICK_CLIPS = int(_get("FRONTIER_NWM_QUICK_CLIPS", 8))
FINAL_CLIPS = int(_get("FRONTIER_NWM_FINAL_CLIPS", 24))
BATCH_SIZE = int(_get("FRONTIER_NWM_BATCH_SIZE", 2))
# Deterministic RNG seed (judge infra): per-clip seed = SEED + clip_index, so the
# baseline (unpatched) and patched arms draw identical initial noise per clip
# (common random numbers). Makes a no-op patch score exactly 0 and the cached
# baseline a valid CRN partner. Vary only for multi-seed robustness runs.
SEED = int(_get("FRONTIER_NWM_SEED", 42))
# Wall-clock guardrail: the patched rollout must not exceed the baseline's
# generation wall-clock by more than this (relative) — else drift is being
# bought with more compute (the speedup task's axis), so penalize.
WALLCLOCK_TOLERANCE = float(_get("FRONTIER_NWM_WALLCLOCK_TOLERANCE", 0.10))
# Image-asset layout (baked into the images; overridable locally).
REPO = Path(_get("FRONTIER_NWM_REPO", "/opt/nanowm/nano-world-model"))
CKPT = Path(_get("FRONTIER_NWM_CKPT", "/opt/nanowm/ckpts/nanowm-l2-csgo/model_state_dict.pt"))
CSGO_DATA = Path(_get("FRONTIER_NWM_CSGO_DATA", "/opt/nanowm/data/csgo"))
VAL_FILES = Path(_get("FRONTIER_NWM_VAL_FILES", "/opt/nanowm/data/csgo_subset/val_files.txt"))
VAL_STARTS = Path(_get("FRONTIER_NWM_VAL_STARTS", "/opt/nanowm/data/csgo_subset/val_starts.npy"))
BASELINE_CACHE = Path(_get("FRONTIER_NWM_BASELINE_CACHE", "/opt/nanowm/baseline/baseline_metrics.json"))
SMOKE = os.environ.get("FRONTIER_NWM_SMOKE", "0") == "1"
