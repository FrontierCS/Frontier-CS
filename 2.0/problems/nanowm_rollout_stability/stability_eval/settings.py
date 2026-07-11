"""Task settings for nanowm_rollout_stability, overridable via config.yaml
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
# Drift metric: mean LPIPS over the drifted tail (frames >= this index). This is
# the NOMINAL tail used by the cached agent-role path; the SCORED (role=final) run
# derives its tail from the randomized horizon below (tail_start_for).
DRIFT_TAIL_START = int(_get("FRONTIER_NWM_DRIFT_TAIL_START", 60))

# --- Anti-overfit: randomized SCORED horizon (audit #7) ----------------------
# A patch can only target the scored tail window if it knows the rollout's
# absolute frame positions. `df_sample` (the agent's editable scope) never
# receives rollout_length -- only the fixed model window -- so a submission can
# only HARDCODE it: the codex 7.83% run hardcoded a module counter with period 76
# (== ROLLOUT_LENGTH-HISTORY_LENGTH) and ramped EXTRA history-stabilization onto
# frames >= DRIFT_TAIL_START, i.e. it overfit the fixed judge horizon to dump its
# intervention exactly on the scored tail. Defeat that by drawing the SCORED
# horizon at random per run from [ROLLOUT_LENGTH_MIN, ROLLOUT_LENGTH] and deriving
# the tail from it. Drawn DOWNWARD only (<= nominal) so no extra GT headroom is
# needed and the held-out clip count is unchanged; decided ONCE on the judge and
# threaded to every arm/chunk so CRN pairing and chunk bit-identity hold (both
# arms + all chunks share one horizon; the per-batch global-index seed is
# untouched). A hardcoded-period counter then no longer maps to frame position
# (L-HISTORY != 76, so the phase drifts across clips and the ramp sprays at random
# frames), collapsing position-targeting back to a general -- legitimate -- drift
# reducer (e.g. an input-staleness-keyed schedule), which is exactly the task.
# The SCORED horizon is drawn from [MIN, MAX] with MAX well BELOW the nominal
# ROLLOUT_LENGTH (the value the agent-role QUICK loop runs at and can therefore
# measure during dev). What this defeats: the codex 7.83% submission HARDCODED a
# counter period 76 (== nominal 80 - HISTORY 4) and a frame-64 ramp tuned to the
# disclosed horizon 80, dumping extra stabilization exactly on the scored tail. The
# margin matters -- empirically (test_antihack_horizon) that fixed ramp stays
# ~aligned for horizons within ~6 of 80, but for horizons <=72 it MISFIRES (its
# expected tail-targeting over a [64,72] band is ~0, even slightly NEGATIVE), so
# the concrete shipped overfit is neutralized. `df_sample` never receives the
# horizon, so a submission can only hardcode it; randomizing (undisclosed, < the
# measurable nominal) leaves only a HORIZON-ROBUST "stabilize deeper frames more"
# schedule, which responds to genuine accumulated drift and generalizes -- i.e. the
# legitimate behaviour the hack was imitating, not the overfit. MAX <= nominal keeps
# the held-out clip count and GT headroom unchanged (shorter rollouts need <=
# headroom). NOTE: lowering the horizon moves the scored tail earlier; the relative
# drift metric is ~horizon-robust but the band's SNR must be re-confirmed on H100
# (the calibrated effect was measured at tail>=60); MIN/MAX are env-tunable to widen
# the margin (stronger anti-hack) or raise it (closer to the calibrated SNR).
ROLLOUT_LENGTH_MIN = int(_get("FRONTIER_NWM_ROLLOUT_LENGTH_MIN", 64))
ROLLOUT_LENGTH_MAX = int(_get("FRONTIER_NWM_ROLLOUT_LENGTH_MAX", 72))
TAIL_FRAMES = int(_get("FRONTIER_NWM_TAIL_FRAMES", 20))  # scored tail = last N frames


def draw_final_rollout_length() -> int:
    """Pick the SCORED rollout horizon for one run. Random per run (fresh entropy)
    so the agent cannot have measured/hardcoded it during the agent-role QUICK loop
    (which stays at the nominal ROLLOUT_LENGTH); pin via FRONTIER_NWM_ROLLOUT_NONCE
    for reproducible validation. Bounded to [ROLLOUT_LENGTH_MIN, ROLLOUT_LENGTH_MAX]
    with MAX < nominal (so GT headroom and the held-out clip count are unchanged AND
    the scored horizon never equals the agent-measurable nominal). A band of width 0
    (MIN >= MAX) disables randomization and pins to MAX (e.g. CI / pinned validation)."""
    import random
    lo = min(ROLLOUT_LENGTH_MIN, ROLLOUT_LENGTH_MAX)
    hi = min(ROLLOUT_LENGTH_MAX, ROLLOUT_LENGTH)   # never exceed the nominal headroom
    if lo >= hi:
        return hi
    nonce = (os.environ.get("FRONTIER_NWM_ROLLOUT_NONCE") or "").strip()
    rng = random.Random(nonce) if nonce else random.Random()
    return rng.randint(lo, hi)


def tail_start_for(rollout_length: int) -> int:
    """Scored tail window = the last TAIL_FRAMES frames of the (possibly
    randomized) horizon, floored at 1 so the filter always selects >=1 frame."""
    return max(1, int(rollout_length) - TAIL_FRAMES)
# Eval set sizes — drift reductions are small, so enough clips to resolve them
# above per-clip noise (validated under CRN pairing: 3 seeds x 22 clips give
# pooled paired t=5.15, p<1e-4 for the reference).
QUICK_CLIPS = int(_get("FRONTIER_NWM_QUICK_CLIPS", 8))
# Full held-out set = the 22 test_split episodes <=200 staged from the 1-200 chunk
# (>22 indexes past the sliced dataset). The scored final uses all 22 for SNR; the
# 80-frame paired rollout (~10h sequentially under strict determinism) is made
# affordable by fanning the clips out across Modal containers (CHUNK_SIZE each),
# bit-identically to the sequential run (per-batch seed keys on the global clip
# index). batch_size=2 => QUICK(8) stays a noise-identical prefix of FINAL.
FINAL_CLIPS = int(_get("FRONTIER_NWM_FINAL_CLIPS", 22))
BATCH_SIZE = int(_get("FRONTIER_NWM_BATCH_SIZE", 2))
# Clips per Modal container when the scored (role=final) pair is fanned out (see
# modal_app.run_pair_remote). Rounded up to a multiple of BATCH_SIZE in orchestrate
# so chunk offsets land on global batch boundaries (-> bit-identical to sequential).
# 22 clips / 4 => 6 parallel chunks; smaller = more parallelism, more load overhead.
CHUNK_SIZE = int(_get("FRONTIER_NWM_CHUNK_SIZE", 4))
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
        "batch_size": BATCH_SIZE, "seed": SEED, "drift_tail_start": DRIFT_TAIL_START,
        "val_files": str(VAL_FILES), "val_starts": str(VAL_STARTS),
    }
    blob = json.dumps(keys, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
