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
# Rollout protocol (the FIXED invocation; the agent's patch changes the sampler
# internals, not these).
ROLLOUT_LENGTH = int(_get("FRONTIER_NWM_ROLLOUT_LENGTH", 50))
HISTORY_LENGTH = int(_get("FRONTIER_NWM_HISTORY_LENGTH", 4))
NUM_SAMPLING_STEPS = int(_get("FRONTIER_NWM_NUM_STEPS", 50))   # nominal reference budget
SCHEDULING_MODE = _get("FRONTIER_NWM_SCHEDULING", "sequential")
HISTORY_STAB = float(_get("FRONTIER_NWM_HISTORY_STAB", 0.02))
# Eval set sizes
QUICK_CLIPS = int(_get("FRONTIER_NWM_QUICK_CLIPS", 4))
FINAL_CLIPS = int(_get("FRONTIER_NWM_FINAL_CLIPS", 16))
BATCH_SIZE = int(_get("FRONTIER_NWM_BATCH_SIZE", 4))
# Deterministic RNG seed (judge infra): per-clip seed = SEED + clip_index, so the
# baseline (unpatched) and patched arms draw identical initial noise per clip
# (common random numbers). Makes a no-op patch score exactly 0 and the cached
# baseline a valid CRN partner. Vary only for multi-seed robustness runs.
SEED = int(_get("FRONTIER_NWM_SEED", 42))
# Quality guardrail: patched rollout LPIPS may rise at most this (relative)
# above the baseline (unpatched seq@50) LPIPS before the score is penalized.
QUALITY_TOLERANCE = float(_get("FRONTIER_NWM_QUALITY_TOLERANCE", 0.03))
# (E) Speedup at which the latency score saturates to 100. The score is
# 100*log2(speedup)/log2(target), so the OLD behaviour (bare 100*log2) was an
# implicit target of 2x -- every solution >=2x capped at 100 and became
# indistinguishable. Raised to 4x so the score keeps a gradient across the
# realistically achievable ~1-4x+ range (causal-prefix ~3x, +bf16 stacks higher).
SPEEDUP_SCORE_TARGET = float(_get("FRONTIER_NWM_SPEEDUP_TARGET", 4.0))
# (A) Faithfulness BACKSTOP: mean LPIPS between the PATCHED and BASELINE rollout
# frames (paired, role=final). Always REPORTED (faithfulness_lpips in metrics); a
# penalty only kicks in past this generous threshold, so it catches an egregious
# rollout SUBSTITUTION (a different sampler dressed up as a speedup) without
# rejecting legitimate iso-quality optimizations. Calibrated on H100: the bf16
# reference drifts 0.206 LPIPS from the fp32 baseline over the 50-frame
# autoregressive rollout (still iso-quality vs GT, but a different trajectory), so
# 0.10 would wrongly punish it -- 0.30 clears bf16 with margin while still flagging
# wildly substituted rollouts (~half-divergent). codex's causal-prefix is ~0.
FAITHFULNESS_TOLERANCE = float(_get("FRONTIER_NWM_FAITHFULNESS_TOL", 0.30))
# Image-asset layout (baked into the images; overridable locally).
REPO = Path(_get("FRONTIER_NWM_REPO", "/opt/nanowm/nano-world-model"))
CKPT = Path(_get("FRONTIER_NWM_CKPT", "/opt/nanowm/ckpts/nanowm-l2-csgo/model_state_dict.pt"))
CSGO_DATA = Path(_get("FRONTIER_NWM_CSGO_DATA", "/opt/nanowm/data/csgo"))
VAL_FILES = Path(_get("FRONTIER_NWM_VAL_FILES", "/opt/nanowm/data/csgo_subset/val_files.txt"))
VAL_STARTS = Path(_get("FRONTIER_NWM_VAL_STARTS", "/opt/nanowm/data/csgo_subset/val_starts.npy"))
BASELINE_CACHE = Path(_get("FRONTIER_NWM_BASELINE_CACHE", "/opt/nanowm/baseline/baseline_metrics.json"))
SMOKE = os.environ.get("FRONTIER_NWM_SMOKE", "0") == "1"
# Determinism proof switch (judge infra). 0 (default): a missing deterministic
# kernel WARNS and runs nondeterministically. 1: it RAISES instead -- run once on
# H100 to PROVE the model+VAE+metric have no nondeterministic op (and re-establish
# no-op CRN pair -> 0.0 there); production may then stay strict (a fallback -> an
# infra error, never a silently corrupted score) or relax once proven clean.
def _as_bool(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)
STRICT_DETERMINISM = _as_bool(_get("FRONTIER_NWM_STRICT_DETERMINISM", 0))


def config_fingerprint() -> str:
    """Stable hash of every knob that affects the unpatched baseline. Used to key
    the baseline cache and the composed-config filename so a cached baseline is
    only ever reused as a common-random-numbers partner for the IDENTICAL config
    (changing any of these invalidates the cache instead of silently mispairing)."""
    import hashlib
    keys = {
        "model": MODEL, "dataset": DATASET, "rollout_length": ROLLOUT_LENGTH,
        "history_length": HISTORY_LENGTH, "num_steps": NUM_SAMPLING_STEPS,
        "scheduling": SCHEDULING_MODE, "history_stab": HISTORY_STAB,
        "batch_size": BATCH_SIZE, "seed": SEED,
        "val_files": str(VAL_FILES), "val_starts": str(VAL_STARTS),
    }
    blob = json.dumps(keys, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
