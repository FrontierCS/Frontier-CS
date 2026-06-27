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
Identical to nanowm_rollout_speedup: Python-only allowlist (`src/diffusion/**`
only) — `src/sample/sampling_utils.py` is DENIED (it decodes+saves the generated
frames the LPIPS metric reads, so editing it could blur the scored pixels);
deny model/VAE/metric/harness/data; Modal GPU
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

## 7. Update — H100 + CRN hardening (this branch)

All in judge infra (`infra_patches/0001-…`, `stability_eval/`); the agent-editable
sampling scope and the shared 2.0 template are untouched. This matters more here
than for speedup: the drift effect (~6.8%) is the same order as the run-to-run
noise the audit measured, so a noisy baseline is more likely to swamp the signal.

- **GPU is now H100, not L40S** (`config.yaml`, `modal_app.py`) — production
  scoring and the calibrated numbers share one SKU.
- **Determinism enforced** (deterministic kernels + TF32 off in `rollout.py`,
  `CUBLAS_WORKSPACE_CONFIG` exported by the launcher) so per-clip seeding yields a
  bit-stable pipeline, not just identical initial noise.
- **Scored (final) run pairs baseline + patched in one job/GPU/process** (true
  CRN, no cache); the cached path is iterative-only and keyed by a full config
  fingerprint (incl. `drift_tail_start`).
- Also fixed the `stability_eval/settings.py` docstring (was "speedup") and the
  `modal_app` app-name default (was `nanowm-rollout-speedup`).

**Validation status:** scoring/smoke re-verified on CPU (no-op CRN pair → 0.0;
reference reproduces ~6.8; `score_unbounded == score` by construction for a
relative reduction). **GPU/Modal end-to-end on H100 pending maintainer
credentials** — the multi-seed drift numbers must be re-measured on the
production path before being treated as final.

## 8. Update — #7 tail-targeting hack closed (randomized scored horizon, this branch)

The codex 7.83% submission added a module-global call counter (`% 76`, ==
`ROLLOUT_LENGTH − HISTORY_LENGTH`) and ramped extra history-stabilization onto the
late frames, saturating exactly at frame 64 == the scored tail (`drift_tail_start
60`). `df_sample` never receives the horizon, so the only way it could target the
tail was to HARDCODE the disclosed length (the README said "80-frame rollout").

Fix: the **scored horizon is drawn at random per run** from `[64, 72]` (well below
the agent-measurable nominal 80), decided once on the judge and threaded to both CRN
arms and every fan-out chunk; the scored tail is derived from it (`tail = horizon −
TAIL_FRAMES`). CRN + chunk bit-identity preserved (one horizon shared; per-batch
global-index seed unchanged; `MAX ≤ nominal` keeps GT headroom and the 22-clip set).
The README/DESIGN no longer disclose the horizon or the tail index. A no-GPU proof
(`stability_eval/test_antihack_horizon.py`) shows the shipped counter's expected
tail-targeting collapses from 100% (at the disclosed 80) to ≈0% over the band (even
negative at the shorter horizons — its fixed ramp misfires). What survives is a
**horizon-robust** "stabilize deeper frames more" schedule, which is the legitimate
adaptive-stabilization behaviour the hack imitated (responds to real accumulated
drift, generalizes, faithfully cleans the tail). The single-scalar shallowness (#6)
is a separate depth limitation, not a reward-hack — see AUDIT_REPORT for the
H100-sweep-gated redesign. **Pending:** re-confirm the band's SNR on H100 (the
calibrated effect was measured at `tail≥60`); `MIN/MAX` are env-tunable.
