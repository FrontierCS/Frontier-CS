# Design — nanowm_rollout_speedup

## 1. Task

Optimize the inference **latency** of a frozen video world model's
autoregressive long-rollout, at iso-quality. The agent submits a Python-only
patch to the diffusion **sampling** layer of Nano World Models (arXiv:2605.23993);
the judge runs a fixed NanoWM-L/2 CSGO 50-frame rollout, scores wall-clock
speedup over the unpatched baseline, gated by an LPIPS-vs-GT quality guardrail.

Shape and scoring mirror `vllm_llm_serving_optimization` (#145): patch a source
tree, build/run on a Modal GPU from a CPU judge, score `100·log2(speedup)` with
an accuracy guardrail. **No change to the general 2.0 adapter/template** — GPU is
per-problem via Modal.

## 2. Why this is a real task (calibration)

Measured on Della H100, NanoWM-L/2 CSGO, 50-frame rollout, 12 held-out episodes,
LPIPS vs ground truth:

| DDIM steps | speedup | LPIPS-vs-GT | Δ vs seq@50 |
|---|---|---|---|
| 50 (baseline) | 1× | 0.517 | — |
| 20 | 2.5× | 0.543 | +5% |
| 10 | 5× | 0.543 | +5% |
| 5 | 10× | 0.579 | +12% |
| 2 | 25× | 0.676 | +31% |

CSGO has a genuine steps↔quality frontier (paper Fig. 6): naive step-cutting
degrades quality fast (seq@5 = +12%, seq@2 = +31%). With a 3% guardrail, even
seq@20 (+5%) fails, so a winning patch must reproduce ~50-step quality with less
compute via real fast-sampling techniques. (Contrast: on the visually-trivial
PushT domain, seq@2 reproduces seq@250 within the stochastic noise floor — no
frontier; CSGO was chosen precisely because the frontier is real.)

## 3. Patch policy (validated before running)

Python-only (`.py`/`.pyi`), ≤256 KB, no file deletion, safe paths.

- **Allowed:** `src/diffusion/**.py`, `src/sample/sampling_utils.py` (the sampling
  layer: scheduling matrices, the DDIM/diffusion-forcing loop, solvers, caches).
- **Denied:** model (`src/models/**`), VAE (`src/latent_codecs/**`), metric
  (`src/sample/evaluate_metrics.py`), harness (`src/sample/rollout.py`), data
  (`src/wm_datasets/**`), training/eval/utils, native/build/deps.
- **Rejected added-line tokens:** `FRONTIER_*/JUDGE_/HARBOR_/MODAL_/HF_TOKEN`,
  metric/GT/timing identifiers, `os.environ`, `subprocess`, `socket`,
  `time.sleep`, `while True`, hard-coded judge paths — i.e. no benchmark
  detection, env-var leakage, output hard-coding, or timing short-circuits.

The rollout invocation (length/context/nominal-steps/scheduling) is fixed by the
judge; the agent changes only sampler internals (cf. #145 fixing the serving
config and patching the scheduler).

## 4. GPU on Modal (judge stays CPU)

`speedup_eval/modal_app.py` runs one rollout in a Modal GPU function from baked
assets (NanoWM checkout + L/2 CSGO ckpt + held-out CSGO episode subset);
`orchestrate.run_pair` computes the cached vanilla baseline once and the patched
run per submission. A `local` backend (`orchestrate._run_local`) runs the same
`speedup_eval.runner` on a directly-visible GPU — this is the path validated on
Della H100. End-to-end Modal execution awaits maintainer Modal credentials.

## 5. Scoring

`speedup_eval/scoring.py` (shared with the public test): geomean rollout speedup
→ `clip(100·log2, 0, 100) · quality_multiplier`, where the multiplier is 1.0
within `quality_tolerance` LPIPS rise and decays inverse-proportionally beyond.
`score_unbounded` keeps rewarding speedup past 2×.

## 6. Reference solution

`reference.patch`: a one-line bf16-autocast wrap of the sampling loop in
`gaussian_diffusion.dfot_sample_loop` — a quality-preserving speedup that beats
the fp32 baseline (CI requires reference > baseline). The intended frontier
(DPM-Solver++, caching, distillation) is left to the agent.

**Validated end-to-end on Della H100 (local backend, 4 CSGO clips, 2026-06-12):**
baseline 299.9 s / LPIPS 0.548 → bf16-patched 256.7 s / LPIPS 0.521 ⇒ **1.17×
speedup, quality_multiplier 1.0, score 22.4** (reference > baseline ✓). Patch
policy validated (accepts reference; rejects metric edits + env-var leakage);
smoke path returns 1.0 with the empty reference on CPU. The frontier (seq@2 =
+31% LPIPS) leaves wide headroom above the 1.17× reference for real fast-sampling
patches. **Pending:** end-to-end Modal execution (maintainer credentials).

## 7. Open items for maintainers

- Modal end-to-end run + a deployed `modal_app` app name / GPU type confirmation.
- Bake-asset provenance for the judge image (ckpt + held-out CSGO subset + cached
  baseline metrics); the held-out episode ids are the only hidden component.
- CI smoke (`FRONTIER_NWM_SMOKE=1`, CPU) validates the patch policy + empty
  reference; confirm this matches the repo's CI expectation for GPU/Modal tasks.
