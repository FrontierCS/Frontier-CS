# NanoWM Frontier-CS 2.0 — Audit Report

**Scope:** `nanowm_rollout_speedup` and `nanowm_rollout_stability` benchmark tasks.
**Date:** 2026-06-13. **Audit lead synthesis** over 5 independent auditors + adversarial verifiers.
**Bar applied:** these are benchmark tasks; a *modest* reference is fine (headroom for agents). Real risks are (a) unfair/strawman baseline, (b) reference that does not reliably beat baseline, (c) marginal statistics sold as robust, (d) gameable/leaky metric, (e) over-claim in docs/PR.

This report uses **only findings whose verifier verdict was `real==true`**; refuted findings are excluded. Overlapping findings (many auditors hit the same root causes — unseeded sampling, cached baseline, the 7.2/5.54/3.56 doc spread) are de-duplicated into single problems. All numbers below were independently recomputed with the project's own env (`envs/nanowm/bin/python`, scipy) using the harness's exact tail definition (`groupby(frame_idx).mean()` then mean over `frame_idx>=60`, `is_context` excluded).

---

## Summary

Both tasks rest on a **sound domain choice and clean leakage controls** (C1, C6 survive). The reference solutions *do* beat baseline in every run measured, and the baselines are fair (symmetric harness, the model's own defaults, the in-scope sampling layer is the only lever). The strong claims that this is a strawman baseline, a non-viable task, or a fabricated 7.2% headline were **refuted** on the artifacts.

The genuine residue is concentrated and mostly **low severity**, but one item is **high**:

1. **(HIGH) The metric is unseeded and the baseline is cached, not re-measured paired.** Sampling draws unseeded `th.randn` and the harness pairs a *cached* baseline against a *freshly-run* patched arm. Same-config run-to-run tail-LPIPS noise (~2-3%) is the same order as both the stability effect (~3.6%) and the 3% speedup quality guardrail. Consequence: a no-op patch scores nonzero (random sign), and a true iso-quality speedup patch can trip the guardrail on an unlucky draw. This is the one item that touches *gameability* and *"reliably beats baseline."*

The remaining real items are **documentation/robustness hygiene** (low): three-way numeric inconsistency across docs (stability 3.56 / 5.54 / 7.2; speedup 22.4 / 20.1), a dead per-region timer that silently falls back to full-process wall-clock, a single-seed marginal `t=2.41 (p=0.025)` sold as "reliably," the baseline-cache `>= clips` rule, and absolute-LPIPS tables that include context frames without saying so. None of these, alone, makes a task ill-posed — but the HIGH item plus the doc spread together mean the *magnitude* of the reference margin is overstated and noise-contaminated.

**Bottom line:** ship-able after fixing the seeding/baseline-pairing (1 high) and reconciling the doc numbers. The tasks are well-posed and the references are real; the scoring is just noisier and the docs more optimistic than advertised.

---

## Confirmed Problems (severity-ranked)

### P1 — Unseeded sampling + cached-not-paired baseline makes the metric noisy and gameable  `HIGH`
- **Evidence:**
  - No seed anywhere on the eval path: `grep -rnE 'manual_seed|seed_everything|Generator\(' ` over `nano-world-model/src/sample/rollout.py`, `src/diffusion/df_sample.py`, `src/diffusion/gaussian_diffusion.py`, and both `*_eval/` dirs returns nothing. Initial latent is unseeded `th.randn(*shape, device=device)` (`gaussian_diffusion.py:808`, also `:522,:690`); history-stab `q_sample` noise (`df_sample.py:296`) is unseeded.
  - Baseline is cached and reused, patched runs fresh: `speedup_eval/orchestrate.py:69-91` `_baseline()` reads `S.BASELINE_CACHE` and only reruns if missing/insufficient; `run_pair()` returns `(cached_baseline, fresh_patched)`. Identical pattern in `stability_eval/orchestrate.py`.
  - Same-config noise floor (independent unpatched stab=0.02 runs): tail-LPIPS spread `0.6402 / 0.6518 / 0.6582 / 0.6539` = **0.018 abs / 2.8% rel**. Speedup baseline LPIPS `0.5479` (speedup_val) vs `0.5363` (e2e) = **2.1%** pure run-to-run noise on the same 4 clips.
  - **Smoking gun:** the bf16-autocast reference (a pure precision change, `reference.patch:10`) shows patched LPIPS `0.5206` vs baseline `0.5479` = a **4.97% LPIPS *improvement*** — physically impossible for lowering precision; it is run-to-run noise.
  - Gameability: stability score `= 100*(base_tail - patched_tail)/base_tail` (`scoring.py`); a no-op allowlisted whitespace edit re-runs fresh against the cached baseline and scores ~2-3 pts of random sign. Speedup guardrail tolerance is `0.03` (`settings.py`), within ~1.5× the observed ~2% baseline noise, so an iso-quality patch can be zeroed on an unlucky draw.
- **Why it matters:** hits (d) non-gameable metric and (b) "reliably beats baseline." Scores carry an unacknowledged noise/offset budget; marginal effects are confounded with RNG.
- **Fix:** seed the rollout deterministically keyed to clip id (`torch.manual_seed(hash(clip_id))` before the initial `th.randn`), **and** recompute the baseline on the exact same clips/seed *in the same job* (common random numbers) instead of serving a cached baseline. This is the standard paired/CRN remedy and shrinks the metric noise toward zero for the baseline-vs-patched delta.

### P2 — Mutually inconsistent baselines and scores across docs; no single canonical number  `LOW`
- **Evidence:**
  - Stability reference reported as **three** values for the same intervention: `3.56%` (drift_ref, 22 clips, t=2.41 — reproduced), `5.54%` (stability_val, 16 clips — `DESIGN.md:48-50`, `PR_SUMMARY.md:25`), and `7.2%` / score 7.2 (`CALIBRATION_FINDINGS.md:274`, 24 clips). The `7.2` appears in exactly **one** place (a calibration log) and **is** backed by a real judge run (`calib/logs/eval_e2e_stab_9617933.log`: `score 7.204`, patched tail `0.6068`) — so it is not fabricated, but it is unreconciled and it is the high end of a noisy range.
  - Speedup reference reported as `1.17×/22.4` (`DESIGN.md:78-79`, `PR_SUMMARY.md:14`, `CALIBRATION_FINDINGS.md:253`) vs `1.15×/20.1` (`CALIBRATION_FINDINGS.md:273`) — **two distinct 4-clip runs with different baselines** (299.95s vs 291.36s = 2.95% swing) quoted interchangeably. Cross-pairing the two baselines moves the score **4.2 pts** (18.3 ↔ 22.4), and only the `speedup_val` patched (256.7s/0.521) has a JSON; the `253s/0.535` run has no on-disk patched artifact.
  - `DESIGN.md` mtime is **after** the e2e runs yet still carries the older val numbers — i.e. docs were not reconciled to the later runs.
- **Why it matters:** (e) docs should not over-claim. A reviewer cannot tell which baseline/score is canonical; the most-cited figures are the most flattering (slower baseline / higher reduction).
- **Fix:** pick **one** canonical config per task (the production `final_clips`: stability **22**, speedup 16), run it once paired, and report that single number with its CI across `DESIGN.md` / `PR_SUMMARY.md` / `CALIBRATION_FINDINGS.md`. Restate stability as the artifact-backed range **3.6–7.2% (≈5% typical)**, not a bare 7.2. (The old `7.2`/`24-clip` log predates the shipped asset set: the held-out subset bound to the staged 1-200 data chunk is exactly the 22 test_split episodes ≤200, so `final_clips` is capped at 22 — `24` indexed past the sliced dataset and could only have run on a fuller local data tree.)

### P3 — Speedup timer is dead code; score is full-process wall-clock, and the cached baseline is a single un-repeated run  `LOW`
- **Evidence:**
  - `runner.py:58` sets `NWM_TIME_FILE` and the docstring says "rollout-region timed inside; falls back to total wall," but **nothing writes `gen_seconds.txt`**: `grep -rn 'gen_seconds.txt|NWM_TIME' nano-world-model/src/` returns empty. So `run_rollout` **always** returns `wall = time.time()-t0` (`runner.py:65-76`), timing model load + VAE load + dataset load + the full VAE decode + mp4 save — none of which the allowlisted sampling patch can touch.
  - Linear fit of `outputs/csgo_frontier/summary.tsv` (wall vs steps) gives fixed overhead ≈ 36s of an 851s wall (~4.3%); the bf16 patch can only act on the ~95.7% sampling region, so wall-clock timing is **conservative** (under-credits the agent) — not unfair, but it dilutes the measured speedup and injects overhead variance.
  - Baseline is a single un-repeated run (no median-of-N, no warmup: `grep` for `repeat|median|trials|per_clip` in `orchestrate.py`/`runner.py` is empty), so the cached value biases every agent's absolute score by the ~3% baseline swing (a shared offset, not per-agent noise).
  - `evaluator.py:178` passes `{"all": gen_seconds}` — the advertised per-clip geomean (`scoring.py`) is vestigial (length-1).
- **Why it matters:** (e) misleading internal docstring + dead code; minor dilution of the speedup signal and a ~4-pt shared offset in the headline absolute score. Not gameable (NWM_TIME/gen_seconds are in `FORBIDDEN_TOKENS`).
- **Fix:** either (i) actually implement the per-region timer (write elapsed sampling time to `NWM_TIME_FILE` inside `rollout.py`'s sample loop) so the metric isolates the region the patch can affect, or (ii) drop the dead env-var/fallback and fix the docstring to say "full-process wall-clock." Measure the baseline as median-of-N (or paired in-job per P1).

### P4 — Stability effect is marginal and single-seed; "reliably beats baseline" overstates a `p=0.025`, one-seed result  `LOW`
- **Evidence:** recomputed on `outputs/drift_ref` (22 clips, tail≥60): mean reduction `0.0232`, `SE 0.0096`, **`t=2.410, p=0.0252`**, win `16/22=73%` — exactly matching `DESIGN.md:25`. But it is barely below α=0.05, on **one model seed** (no seed replication in `outputs/`), and window-fragile: over *all* generated frames (4–79) the same clips give only `+2.04%`, `t=1.16`, `p=0.26` (NS) — significance is concentrated in the last 20 frames. (Verifier note: a Wilcoxon signed-rank *confirms* it, `W=60, p=0.032`, and no single-clip drop flips significance, so the effect is real, just marginal.)
- **Why it matters:** (c) marginal statistics. The hidden-set 24-clip final could land NS by chance; "reliably" is stronger than a single-seed α-edge result supports.
- **Fix:** report **multi-seed** (≥3 model/sampling seeds) and the **Wilcoxon** alongside the `t`, and soften "reliably beats baseline" to "beats baseline (paired t=2.41, p=0.025, 73% win, 22 clips; Wilcoxon p=0.03)." Increasing `final_clips` or averaging seeds tightens the CI.

### P5 — Baseline-cache `>= clips` rule pairs different-sized clip sets across roles  `LOW`
- **Evidence:** `orchestrate.py:74` `if data.get('clips',0) >= clips: return data` — a cached 24-clip baseline is served to an 8-clip QUICK eval while patched runs only 8 clips. Per-clip tail-LPIPS std is `0.041` (6.3% rel). *However* clip selection is a deterministic seeded prefix (`rollout.py` iterates a fixed order, `random_seed=42`), so the 8-subset is **nested** in the 24-set; the actual prefix-mean offset (recomputed: first-8 vs all-22 = **−0.19%**, negative → clamps a no-op to 0) is ~1/19 of the effect, not "the same size." Real but small.
- **Why it matters:** (d) cleaner to compare like-for-like; scores not strictly comparable across QUICK (agent) and FINAL roles.
- **Fix:** require the cached baseline clip count to **equal** the requested count and be computed on the identical clip ids (subsumed by the P1 in-job paired-baseline fix).

### P6 — Scoring/labeling hygiene: context-included LPIPS tables and the log2 cap  `LOW`
- **Evidence:**
  - Headline CSGO LPIPS (`0.517/0.543/0.579/0.676`, `DESIGN.md:23-27`, header "LPIPS-vs-GT") are **all-rows** means including the 48 near-zero context frames (LPIPS ≈ 0.006, 8% of rows); generated-only means are ~0.045 higher (`0.561/0.590/0.629/0.735`). **Scoring-neutral** (the relative guardrail cancels the constant context block — verified the rel-change differs by 0.004pp) and the **judge uses the same all-rows convention** (`runner.py:88` `mean()` over all rows), so it is a labeling nit, not a metric defect.
  - `score_from_speedup = clip(100*log2(s),0,100)` caps the **primary** score at 2× (`scoring.py:33-36`). The "true 4× is indistinguishable from 2×" concern is rebutted: `scoring.py:66`/`evaluator.py:194` also return `score_unbounded` (uncapped) and `metrics` carry raw `geomean_speedup` — the repo-wide Frontier-CS 2.0 convention, matching `bboplace`.
- **Why it matters:** (e) minor; a reader calibrating the 3% tolerance against `0.517` is reasoning about a diluted absolute number.
- **Fix:** add a one-line note to the LPIPS tables: "(all frames incl. 4 context frames; same convention the judge scores on)." No scoring change needed.

---

## Standing Conclusions (claims that SURVIVED scrutiny)

| Claim | Verdict | Recomputed support |
|---|---|---|
| **C1 — CSGO has a real step↔quality frontier** | **SURVIVES** | Gen-only LPIPS strictly orders at the named corners: seq@2 `0.7345` > seq@5 `0.6285` > seq@20 `0.5901` > seq@50 `0.5612`; +30.9% seq2-vs-seq50. (Caveat: seq@10≈seq@20 flat-spot, `0.5903` vs `0.5901` — disclose, but the {2,5,20,50} corners are monotone.) |
| **C2 — speedup reference ~1.15–1.17× at iso-quality, fair baseline** | **SURVIVES** (modest, as intended) | `speedup_val` 299.95s→256.73s = **1.168×**, score 22.45; patched LPIPS `0.5206` < baseline `0.5479` (quality-neutral, guardrail not tripped). Baseline is symmetric (one rollout cmd for both arms, `runner.py:59-64`); the native `--use_fp16` flag is walled off by the denylist (`evaluator.py` denies `src/models/**`, `src/sample/rollout.py`), so fp32 is the genuine in-scope default — **not** a strawman. |
| **C3 — stability reference reliably beats baseline (modest headroom)** | **SURVIVES** (magnitude is noisy; see P2/P4) | Reference > baseline in **every** run: drift_ref 22-clip `+3.56%` (t=2.41, p=0.025, 73% win), stability_val 16-clip `+5.54%`, e2e 24-clip `+7.2%` — all positive, iso-wall-clock. Baseline pinned at the model's own default stab=0.02 (`default.yaml:58`) is fair. The "non-viable / worst-point baseline / 0.00 better" attacks were **refuted**: on the shipped 80-frame config the lever is monotonic (0.02→0.10→0.20 decreasing) and a 0.00 revert *increases* drift (scores 0). |
| **C4 — RT-1 / Rope correctly rejected as domains** | **SURVIVES** | RT-1 frontier is U-shaped (min at seq@5 under both conventions, never monotone) → speedup trivial, correctly rejected. Rope rejection rests on a documented **data-block** (RAW per-episode h5, 21 frames/episode) + the paper's own Table 7 LPIPS `0.056`; the empty `rope_frontier/` stub is a cosmetic leftover, not the cited evidence. |
| **C5 — patch policy blocks gaming** | **PARTIALLY SURVIVES** | The denylist + `FORBIDDEN_TOKENS` (`evaluator.py:51-57`) and the LPIPS-vs-GT guardrail block the *semantic* attacks tested: config-conditioned step-cutting can't earn quality_mult=1.0 (seq@20 is +5.2% > 3% tol), and a disk-cache attack can't fabricate iso-quality speedup (different clips each call; repo `rmtree`'d each run). The **residual** gap is P1 (unseeded single-replicate guardrail), not benchmark-detection. |
| **C6 — no train/test leakage** | **SURVIVES (clean)** | All 22 `data/csgo_subset/val_files.txt` ∈ `csgo_splits/test_split.txt` (22/22), **0** ∈ `train_split.txt`; train/test disjoint; val ids not git-tracked. (The C6 brief mis-names `gen_episodes.py`, a PushT utility, as provenance — but the real guarantee is the verified test_split membership, and the *substantive* artifact `settings.py VAL_FILES/VAL_STARTS` is correct.) |

---

## Recommended Fixes (highest-leverage first)

1. **Seed the rollout + measure baseline paired in-job (P1).** The single highest-leverage change: `torch.manual_seed(clip_id)` before the initial `th.randn`, and replace the cached baseline with a baseline computed on the same clips/seed in the same job (common random numbers). Removes the gameability (no-op → ~0) and shrinks the metric noise that contaminates both references' margins.
2. **Reconcile the docs to one canonical number per task (P2).** Run the production `final_clips` config once (stability 22, speedup 16), report that single value + CI everywhere; restate stability as 3.6–7.2% (≈5% typical) and pick one speedup baseline.
3. **Fix the timer + baseline measurement (P3).** Either implement the per-region sampling timer (so the metric isolates the patchable region) or delete the dead `NWM_TIME_FILE` path and correct the docstring; measure the baseline as median-of-N (or paired per #1).
4. **Report multi-seed + Wilcoxon for stability and soften "reliably" (P4).** ≥3 seeds, Wilcoxon alongside the t-test; word the claim to the α-edge it actually is.
5. **Require `== clips` on the cached baseline and label the LPIPS tables (P5, P6).** Equal nested clip sets; one-line "(all frames, judge convention)" note on the LPIPS-vs-GT tables.

---

## Methodology & limits of this audit

- **Inputs:** 5 independent auditor findings, each with an adversarial verifier verdict. I used **only** findings with `verdict.real==true` and merged duplicates (the unseeded-baseline root cause appeared in ~6 findings; the 7.2/5.54/3.56 spread in ~5).
- **Independent recomputation:** every load-bearing number above was re-derived from the raw artifacts with the project's own `envs/nanowm/bin/python` + scipy, using the harness's exact tail definition (`groupby(frame_idx).mean()`, mean over `frame_idx>=60`, `is_context` excluded). Confirmed: drift_ref 22-clip (3.56%, t=2.41, p=0.025, 16/22), speedup_val 1.168×/22.45, the 2.95% baseline swing → 4.2-pt score swing, the e2e stability log (score 7.204, patched tail 0.6068), CSGO frontier monotonicity, and C6 disjointness (22/22 test, 0 train).
- **What this audit did NOT do:** run the Modal-GPU judge backend end-to-end (validated the local path only); execute new multi-seed rollouts (the single-seed limitation is inferred from the absence of seed-named artifacts and the documented unseeded noise floor); audit tasks other than the two NanoWM rollout tasks.
- **Severity calibration:** applied the benchmark bar — a modest reference and a small speedup are *acceptable*, so several "high"-filed findings (strawman baseline, non-viable task, fabricated 7.2) were correctly **refuted/downgraded** by the verifiers and are excluded here. The one surviving HIGH (P1) is the only item touching gameability + reliable-beat; everything else is doc/robustness hygiene.

---

## Fixes applied + validated (2026-06-14)

All confirmed problems addressed and re-validated on Della H100
(`calib/audit_fix.sbatch`, job 9647587; analysis `calib/audit_fix_analyze.py`; raw in
`outputs/audit_fix/`). Canonical numbers also recorded in `docs/CALIBRATION_FINDINGS.md`.

| # | Fix | Validation result |
|---|---|---|
| **P1** `HIGH` | Deterministic clip-keyed seeding in `rollout.py` (`manual_seed(seed+clip_idx)` per batch, common random numbers); `*_eval` baseline cache keyed by `(== clips, seed)`. | Baseline vs baseline_rep vs **no-op**: per-clip LPIPS Δ = **0.00** → no-op scores **0.15 (speedup) / 0.000 (drift)** ≈ 0 (ungameable). The "impossible" −4.97% bf16 LPIPS improvement is gone → **+1.7%** (bf16 slightly worse, physically correct). |
| **P3** `LOW` | Implemented the real per-region sampling timer (writes `NWM_TIME_FILE`); docstring now accurate. | Speedup is sampling-region only (baseline 1102.1s); residual wall noise **0.24%** (was ~3%). |
| **P4** `LOW` | Multi-seed (42/43/44) + Wilcoxon; softened "reliably" to the actual stats in DESIGN/PR. | Drift reduction **6.8% ± 1.2%** across 3 seeds; pooled **paired t=5.15, p<1e-4, Wilcoxon p<1e-4**, 74% win — no longer marginal (was single-seed t=2.41/p=0.025). |
| **P2** `LOW` | Reconciled to ONE canonical value per task + CI across DESIGN×2 / PR_SUMMARY / CALIBRATION / PR body. | speedup **1.17× / score 22.3**; stability **6.8% / score 6.8**. |
| **P5** `LOW` | Baseline cache now requires `== clips` (+ seed); clip-aligned seeding makes QUICK a noise-identical prefix of FINAL. | Subsumed by P1 determinism. |
| **P6** `LOW` | Labeled the LPIPS tables "(all frames incl. context; judge convention)". | No scoring change (as the audit noted). |

The fix lives in judge infrastructure (`rollout.py` + `*_eval/`, regenerated into
`infra_patches/0001-rollout-judge-infra.patch`) — **outside the agent's editable
sampling scope**, and the shared 2.0 adapter/template is untouched. Standing
conclusions C1–C6 are unaffected (and C3/C5's residual P1 caveat is now closed).

---

## Update — P1 actually closed; H100; reviewer-honesty note (2026-06-21, branch `fix/nanowm-h100-crn`)

A re-review found the 2026-06-14 "P1 fixed" claim above was only **half** true:
deterministic per-clip seeding was added, but `orchestrate._baseline()` still
**served a cached baseline** rather than recomputing it paired in-job, and the
infra patch enforced **no GPU determinism** (`use_deterministic_algorithms`,
TF32-off, `CUBLAS_WORKSPACE_CONFIG` were all absent — and upstream `rollout.py`
turns TF32 *on* at import). Seeding fixes the initial noise but not the
arithmetic, so "the cached baseline is a valid CRN partner" only held on the
H100 single node where determinism happened to apply — not the (then L40S, never
run e2e) production path. P1 was therefore not closed for the scored path.

Now actually closed:
- **Determinism enforced** in the infra patch (`use_deterministic_algorithms(True,
  warn_only=True)`, `cudnn.deterministic`, `benchmark=False`, TF32 disabled) +
  `CUBLAS_WORKSPACE_CONFIG=:4096:8` exported by the launcher before CUDA init.
- **Scored (final) run measures baseline + patched as a true CRN pair** in one
  job/GPU/process (`run_pair(role="final")` → `modal_app.run_pair_remote`), no
  cache. Cached baseline kept only for cheap iterative feedback, now keyed by a
  full **config fingerprint** (incl. `drift_tail_start`).
- **GPU pinned to H100** (was L40S) so the production scoring path and every
  calibrated number in this report share one SKU.

**Reviewer-honesty note (closes audit risk (e), over-claim):** the calibration
artifacts this report cites as evidence — `CALIBRATION_FINDINGS.md`, `outputs/`,
`calib/…sbatch`, job numbers, `PR_SUMMARY.md` — **are not shipped in this repo**
(they live in the author's working tree), so the pre-fix numbers above are
**not independently reproducible from the PR** and should be read as provisional.
The code-level fixes here are CPU-verified (policy/scoring/smoke; no-op CRN pair →
exactly 0.0; reference reproduces 1.17×/22.3 and ~6.8); **GPU/Modal end-to-end on
H100 is still pending maintainer credentials** and must re-establish the no-op≈0
and residual-noise numbers on the production path before the headline margins are
final.

---

## Update — #7 tail-targeting reward-hack closed; #6 scoped (2026-06-25, branch `fix/nanowm-h100-crn`)

A post-mortem of the codex Harbor trials surfaced a concrete reward-hack that the
earlier audit had not (the scored run had not yet been exercised by a real agent):

### #7 — tail window targetable via a hardcoded module counter  `HIGH (closed)`
- **The hack (as shipped, codex 7.83% run).** The winning stability submission added
  a **module-global call counter** in `df_sample` and ramped EXTRA history-stabilization
  onto the rollout's late frames:
  `_STABILITY_ROLLOUT_PERIOD = 76` (== `ROLLOUT_LENGTH 80 − HISTORY_LENGTH 4`),
  `rollout_phase = _stability_rollout_call % 76`,
  `extra = 0.08·clamp((rollout_phase−32)/28)`. `df_sample` is called once per generated
  frame, so at the **disclosed** nominal horizon 80 the counter aligns to the
  generated-frame index and the ramp **saturates exactly at frame 64**, i.e. squarely
  on the scored tail (`DRIFT_TAIL_START = 60`). It contributed ≈ +1 pp over the flat-scalar
  reference (7.83 vs ≈6.8), earned by dumping the intervention on the scored window
  rather than reducing drift generally. Slips the static policy (a module counter is
  not a forbidden token).
- **Root enabler.** `df_sample` (the agent's editable scope) never receives
  `rollout_length`, so a submission can only HARDCODE the horizon — which it learned
  from the **README ("80-frame rollout")** and could measure during the agent-role QUICK
  loop.
- **Fix (this branch).** The SCORED (role=final) horizon is now **drawn at random per run**
  from `[ROLLOUT_LENGTH_MIN, ROLLOUT_LENGTH_MAX] = [64, 72]` (well below the
  agent-measurable nominal 80), decided ONCE on the judge and threaded to every arm /
  fan-out chunk (`settings.draw_final_rollout_length`; `orchestrate.run_pair`;
  `runner.evaluate(rollout_length=…)`; `modal_app` spec). The scored tail is derived
  from it (`tail_start = horizon − TAIL_FRAMES`). CRN pairing and chunk bit-identity are
  preserved (both arms + all chunks share one horizon; the per-batch global-index seed is
  unchanged; `MAX ≤ nominal` so GT headroom and the 22-clip set are unchanged). The
  README/DESIGN no longer disclose the horizon or tail index.
- **Verification (no GPU; `stability_eval/test_antihack_horizon.py`).** Replaying the
  exact shipped counter, its **expected** tail-targeting over the `[64,72]` band collapses
  from +0.064 (100% at the disclosed horizon 80) to **+0.00002 (≈0%)** — and is *negative*
  for horizons ≤68, because the fixed period-76/frame-64 ramp misfires onto non-tail frames
  at the shorter horizons. So the concrete shipped overfit is neutralized.
- **What deliberately survives (not a hack).** A **horizon-robust** "stabilize deeper
  frames more" schedule (keyed on a runtime signal — per-clip call index reset at the RNG
  reseed, or context staleness — rather than a hardcoded period) can still raise tail
  quality (~70% of the no-defense ceiling in the diagnostic). That is the **legitimate**
  behaviour the hack imitated: it responds to genuine accumulated drift, generalizes across
  horizons/content, and faithfully cleans the tail via less-contaminated context (LPIPS-vs-GT
  rewards real fidelity, not cosmetic blur — `sampling_utils.py`, the decode/save plumbing,
  is already DENIED). Randomization converts the overfit into *either-legitimate-or-broken*,
  which is the goal. **Caveat:** lowering the horizon moves the tail earlier than the
  calibrated `tail≥60`; the relative drift metric is ~horizon-robust but the band's SNR must
  be re-confirmed on H100. `MIN/MAX` are env-tunable (widen for stronger anti-hack, raise
  toward 80 for the calibrated SNR).
- **Re-verification note (the "partly" survivor is not a practical hack).** A second audit
  suggested a counter with a period grid-searched to `[64,72]` (≈58-62) recovers ~5% of the
  targeting ceiling. Two reasons this is not a meaningful reward-hack: (1) **the band is NOT
  disclosed or observable.** `[64,72]`/`MIN/MAX` live ONLY in the judge-internal `config.yaml`
  `evaluation` block (read via `task_config.json` on the judge); they are absent from
  `harbor/` (the agent workspace) and the agent-facing `environment` string, and the
  agent-role QUICK loop runs at the nominal 80 — so the agent can only calibrate to 80 (period
  76), which collapses to ≈0 on the real band. The grid-search premise ("calibrate on the
  disclosed band during dev") is false. (2) Even granting a leaked band, the residual is ~5%
  of ceiling and **weaker than the flat-`0.20` reference**, with a mechanism (more stabilization
  at greater frame depth) that responds to genuine accumulated drift — i.e. the legitimate
  survivor, not a metric exploit. **Control:** keep the band judge-internal (never ship the
  `evaluation` block to the agent); for belt-and-suspenders the bounds can be jittered per run
  via the nonce. No code change needed; documented as the accepted residual.

### #6 — task collapses to tuning the `history_stabilization_level` scalar  `MEDIUM (scoped, not a reward-hack)`
- The dominant lever is a single exposed scalar: the reference IS `stab→0.20` and yields
  ≈6.8% by itself; codex's per-frame age-profile + the (now-defeated) counter added only
  ~1 pp. This is a **depth/ceiling** limitation (the headline difficulty is shallow), **not**
  a reward-hack — bumping the exposed knob is the intended lever, just a shallow use of it.
- The #7 randomization partially helps (it forces any position-dependent gain to be earned
  *generally*, not on a fixed window), but does not raise the ceiling. **A real fix is a
  recalibrated redesign** (gated on an H100 sweep, so deferred here): set the *baseline*
  `history_stab` to the best-constant value found by a sweep so that merely raising the
  scalar yields ≈0, and ship a NEW reference that is a genuinely better *schedule/mechanism*
  (e.g. drift-keyed adaptive re-anchoring). Until that sweep, the task remains solvable-but-
  shallow; documented here rather than silently shipped as "hard."

### Cross-task hardening shipped alongside #7 (frozen-model guard + faithfulness fail-closed)
A reward-hack audit of the FIXED branch (4 parallel auditors + synthesis) confirmed the
#7 fix is CLEAN with zero regressions (CRN pairing, chunk bit-identity, cached-baseline
validity all preserved) and the scoring math of BOTH tasks is clean (only cosmetic
notes). It surfaced one cross-cutting gap — the model-frozen invariant was not
structurally enforced (the speedup causal-prefix `temp_embed` gray area): a sampler
patch could persistently mutate the frozen model and the static policy can't see a
runtime monkeypatch. Closed in BOTH tasks:
- **Frozen-model guard, actively wired:** `{speedup,stability}_eval.runner.inject_frozen_guard()`
  inlines a param fingerprint into the copied `rollout.py` at apply-time (after the
  agent patch; rollout.py is denied to the agent) — snapshot after `model.eval()`,
  verify before the final `print`. A restored transient reshape (causal-prefix) passes;
  a persistently-mutated model hard-errors → scored 0. Fail-closed if the anchors move.
  Unit-tested (`test_inject_frozen_guard.py`, `speedup_eval/test_frozen_model_guard.py`).
  Matters more for stability (no faithfulness backstop) than speedup.
- **Speedup faithfulness fail-closed:** `evaluator.py` now returns 0 (not
  `faithfulness_mult=1.0`) when `role=="final"` and `faithfulness_lpips` is None, so the
  active model-mutation defense (patched-vs-baseline frame LPIPS) can't be silently
  disabled.
- Cosmetic: corrected the wallclock-multiplier comment (≈0.556 at +tol, 0.5 at
  grace+tol). Net: no exploitable reward-hack or scoring overfit remains on the
  authoritative scored path of either task (remaining items are #6 depth + the
  acknowledged sum-preserving-fingerprint residual, both backstopped).
