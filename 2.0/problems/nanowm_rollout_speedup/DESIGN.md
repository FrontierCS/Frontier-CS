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
LPIPS vs ground truth (means over **all** frames incl. the 4 context frames — the
same convention the judge scores on; generated-only means are ~0.045 higher):

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

- **Allowed:** `src/diffusion/**.py` (the sampling layer: scheduling matrices, the
  DDIM/diffusion-forcing loop, solvers, caches). `src/sample/sampling_utils.py` is
  DENIED — it decodes+saves the frames the LPIPS guardrail reads (editing it could
  blur the scored pixels to mask a quality regression).
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

`speedup_eval/modal_app.py` runs rollouts in a Modal GPU function from baked
assets (NanoWM checkout + L/2 CSGO ckpt + held-out CSGO episode subset). For the
SCORED (final/verifier) run, `orchestrate.run_pair(role="final")` measures the
vanilla baseline and the patched arm back-to-back on one GPU in one job (no
cache) — see §8. The cached vanilla baseline is used ONLY for the cheap iterative
(agent-role) feedback path, keyed by `settings.config_fingerprint()`. A `local`
backend (`orchestrate._run_local` / `_run_pair_local`) runs the same
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

**Validated end-to-end on Della H100 (local backend, 16 CSGO clips, seed 42,
sampling-region timed):** baseline 1102.1 s / LPIPS 0.523 → bf16-patched 944.0 s /
LPIPS 0.532 ⇒ **1.17× speedup, LPIPS +1.7% (within the 3% guardrail),
quality_multiplier 1.0, score 22.3** (reference > baseline ✓). The judge seeds the
rollout deterministically per clip (common random numbers), so the baseline and
patched arms share initial noise: a **no-op patch scores 0.15 (≈0, ungameable)**
and residual wall-clock noise is **0.24%** (the region timer excludes model/VAE/
dataset load and the VAE decode the patch cannot touch). Patch policy validated
(accepts reference; rejects metric edits + env-var leakage); smoke path returns
1.0 with the empty reference on CPU. The frontier (seq@2 = +31% LPIPS) leaves wide
headroom above the 1.17× reference for real fast-sampling patches. **Pending:**
end-to-end Modal execution (maintainer credentials).

## 7. Open items for maintainers

- Modal end-to-end run + a deployed `modal_app` app name / GPU type confirmation.
- Bake-asset provenance for the judge image (ckpt + held-out CSGO subset + cached
  baseline metrics); the held-out episode ids are the only hidden component.
- CI smoke (`FRONTIER_NWM_SMOKE=1`, CPU) validates the patch policy + empty
  reference; confirm this matches the repo's CI expectation for GPU/Modal tasks.

## 8. Update — H100 + CRN hardening (this branch)

Changes since the audit, all in judge infra (`infra_patches/0001-…`, `speedup_eval/`)
— the agent-editable sampling scope and the shared 2.0 template are untouched:

- **GPU is now H100, not L40S** (`config.yaml`, `modal_app.py`). The reference,
  noise floor, and OOM-decode tuning were all calibrated on H100, so the
  production scoring path and the validated numbers now share one GPU SKU
  (closes the hardware-mismatch risk).
- **Determinism is enforced, not assumed.** The infra patch now sets
  `torch.use_deterministic_algorithms(True, warn_only=True)`,
  `cudnn.deterministic=True`, `benchmark=False`, and **disables TF32** (the
  upstream `rollout.py` enabled it at import — a real run-to-run noise source the
  earlier patch left on); the launcher exports `CUBLAS_WORKSPACE_CONFIG=:4096:8`
  before CUDA init. Per-clip seeding alone (the audit's P1 partial fix) fixes the
  initial noise but **not** the arithmetic; this makes the kernels bit-stable so a
  cached/separate baseline is actually a valid common-random-numbers partner.
- **The scored (final) run measures baseline + patched as a true CRN pair** in
  one job/GPU/process (`orchestrate.run_pair(role="final")` →
  `modal_app.run_pair_remote`), no cache — airtight even if residual
  nondeterminism survives. The cheap cached-baseline path is kept only for the
  iterative (agent) role, and its cache key is now a full **config fingerprint**
  (model/dataset/rollout/steps/scheduling/stab/batch/seed/val-set), so a config
  change invalidates rather than mispairs.

**Validation status:** policy/scoring/smoke re-verified on CPU (no-op CRN pair →
exactly 0.0; reference reproduces 1.17×/22.3; hardened token list still accepts
the reference and `model.eval()`/`torch.compile()` while rejecting `/opt/nanowm`,
`*.hdf5`, and `os.getenv` peeks). **GPU/Modal end-to-end on H100 is still pending
maintainer credentials** — the determinism + paired-baseline numbers (no-op ≈ 0,
residual noise) must be re-measured on the production H100 path before the
headline margins are treated as final.

## 9. Update — frozen-model guard for the causal-prefix `temp_embed` gray area

The reference-class causal-prefix optimization (codex's 2.87×, reward 1.0) is a
LEGITIMATE, FP-exact inference optimization: NanoWM is causal (`causal: true`,
frame t attends only to ≤ t) and the sequential diffusion-forcing schedule denoises
one frame at a time, so the baseline harness wastefully runs the model on the full
window every DDIM step while only a short causal *prefix* is active. Cropping to that
prefix cannot change the kept frames' outputs (verified bit-exact: SDPA causal crop
diff 0.0, full temporal-path replication 3e-8 ≈ fp32 ε) — patched LPIPS 0.5234 vs
baseline 0.5235. It edits only `src/diffusion/gaussian_diffusion.py`, trips no
forbidden token, and never touches the metric or scored pixels.

The one wrinkle: to run the unmodified forward on the cropped window it **temporarily
reshapes `module.temp_embed`** (a frozen-tree `src/models/**` nn.Parameter) from the
allowed sampler, then RESTORES it via try/finally. That is exact and reversible, but
the static policy (path allowlist + token scan) cannot see a runtime attribute
monkeypatch, so nothing structurally stops a *different* patch from **persistently**
mutating the frozen model (e.g. swapping in blurred/distilled weights to win
wall-clock). Hardening (`speedup_eval/frozen_model_guard.py`, unit-tested in
`speedup_eval/test_frozen_model_guard.py`): a cheap dynamic invariant — fingerprint
the model params after load, re-check after the rollout; a restored transient reshape
(causal-prefix) passes, a left-mutated model hard-errors (→ submission scored 0). The
residual (a transient swap restored before the check) stays backed by the faithfulness
check below. **Wiring is ACTIVE, not pending:** `speedup_eval.runner.inject_frozen_guard()`
inlines the guard into the copied `rollout.py` at apply-time (after the agent patch;
rollout.py is denied to the agent), so it runs on every rollout in both backends —
fail-closed if the anchors move, and unit-tested (`test_frozen_model_guard.py`,
`test_inject_frozen_guard.py`). The complete alternative (make the model natively slice
`temp_embed`/temporal-rope to the active window so causal-prefix needs NO model touch,
then statically forbid model mutation) is left as the deeper maintainer option.

**The primary, always-active defense against model mutation is the faithfulness check**
(patched-vs-baseline frame LPIPS on the scored pair): any mutation that changes the
OUTPUT frames raises faithfulness and is penalized; an iso-output mutation is a
legitimate faster-equivalent. It is now **fail-closed** — `evaluator.py` returns 0 (not
`faithfulness_mult=1.0`) if faithfulness could not be computed on a `role=="final"` run,
so the backstop cannot be silently disabled. The frozen-model guard is defense-in-depth
on top of it (catching an iso-output-but-still-mutated model).
