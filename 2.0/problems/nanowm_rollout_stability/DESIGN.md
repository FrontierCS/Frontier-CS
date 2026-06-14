# Design — nanowm_rollout_stability

## 1. Task (the dual of nanowm_rollout_speedup)
- **speedup**: minimize wall-clock at iso-quality.
- **stability**: minimize long-horizon **drift** (tail-frame LPIPS-vs-GT) at
  iso-**wall-clock**.

Agent submits a Python-only patch to the NanoWM diffusion sampling layer; judge
runs a fixed 80-frame NanoWM-L/2 CSGO rollout (50 steps) on a Modal GPU and
scores relative tail-drift (frames ≥ 60) reduction vs the unpatched baseline,
gated by a wall-clock guardrail. Same #145-style shape (patch + metric +
guardrail + Modal GPU; general adapter/template untouched).

## 2. Why it's a valid HARD task (calibration)
Long CSGO rollouts saturate to a ~0.65-LPIPS "plausible-but-wrong" tail; at fixed
compute the drift is largely model-intrinsic, so reducing it is genuinely hard.
But it is NOT impossible: a paired test (NanoWM-L/2, 80-frame, tail f≥60) shows
the rollout PROCEDURE moves drift reliably above noise —

| setting (fixed steps=50) | tail-drift (mean over 3 seeds) |
|---|---|
| stab=0.02 (baseline) | 0.655 |
| stab=0.20 (reference) | **0.610** |

With deterministic common-random-numbers pairing (the judge seeds each clip, so
baseline and patched share initial noise), the reference reduces tail-drift by
**6.8% ± 1.2% across 3 seeds** (per-seed 8.3 / 6.2 / 6.1%, 74% per-clip win);
pooled over 66 paired clip-runs the effect is **paired t=5.15, p<1e-4, Wilcoxon
p<1e-4**. So a clearly-better-than-baseline reference exists (task well-posed/
solvable); substantially beating it requires real drift-reduction work (the open
challenge). CRN pairing was essential: an unpaired/unseeded read diluted the
effect into noise (the original marginal single-seed t≈2.4), so the judge now
seeds deterministically and a no-op patch scores exactly 0.

## 3. Fixed-compute constraint (why it's distinct from speedup)
Adding denoising steps reduces drift (paper Fig 6) but costs compute — that's the
speedup axis. A **wall-clock guardrail** (patched gen time ≤ baseline × 1.10,
else the score multiplier decays) forces the agent to reduce drift *at iso-
compute*: stabilization, scheduling-matrix design, drift-aware caching that frees
time for re-grounding, periodic context re-anchoring, error correction, solvers.

## 4. Patch policy / GPU / scoring
Identical to nanowm_rollout_speedup: Python-only allowlist (`src/diffusion/**`,
`src/sample/sampling_utils.py`), deny model/VAE/metric/harness/data; Modal GPU
from a CPU judge (`stability_eval/{runner,orchestrate,modal_app}.py`); smoke
score 1.0 when GPU/Modal unconfigured (local CI). Score =
`clip(100·(base_tail−patched_tail)/base_tail,0,100)·wallclock_mult`.

## 5. Reference
`reference.patch`: one-line history-stabilization bump (stab→0.20) in
`df_sample.dfot_sample` — the calibrated reliable drift reducer (§2).
**Validated end-to-end on H100 (22 clips × 3 seeds, local backend, CRN-paired):**
tail-drift 0.655 → 0.610 at iso-wall-clock (gen-time Δ ≤0.2%, wallclock_mult 1.0)
⇒ **6.8% ± 1.2% reduction, score 6.8 > baseline** ✓ (pooled paired t=5.15,
p<1e-4; a no-op patch scores 0.000). Patch policy + smoke pass.

## 6. Open items for maintainers
Modal end-to-end run; bake-asset provenance (ckpt + held-out CSGO subset +
cached baseline); confirm final_clips gives stable scoring on the judge's hidden
set (the small effect needs ~20+ clips).
