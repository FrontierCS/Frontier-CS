# PR: add `nanoslm_hybrid_arch_design` (Frontier-CS 2.0)

## What

A new open-ended 2.0 problem: design a **hybrid language-model architecture**
(attention + linear-recurrent mixers) that reaches the lowest held-out
**bits-per-byte (`val_bpb`)** when trained from scratch under a **fixed
wall-clock budget on a single H100**. The agent submits one `model.py` (full
architecture freedom); the hidden judge trains it under a locked dolma2-BPE
recipe and scores `val_bpb` against a locked baseline architecture
(pure-attention `olmo3_190M`) trained under the identical budget.

Adapts the Genesys system ("Language Modeling by Language Models",
arXiv:2506.20249) into a bounded, ungameable, single-objective task — the
hybrid architecture discovery starting from Olmo Hybrid (arXiv:2604.03444). Structurally mirrors
`nanowm_rollout_speedup` / `vllm_llm_serving_optimization`: patch/file
submission, Modal H100, CPU judge, latency/quality-style guardrails, CRN
determinism.

## Problem id / scoring

- id: `nanoslm_hybrid_arch_design` (Harbor id `frontier-cs-2-0-nanoslm-hybrid-arch-design`)
- metric: held-out `val_bpb` = total NLL (bits) / held-out BYTES, over the
  dolma2 BPE tokenizer (vocab 100278). Normalizing by BYTES (not tokens) is what
  makes it tokenizer-independent and ungameable. Lower is better. (`val_ppl` is
  reported for readability only and is NO LONGER equal to `2^val_bpb`.)
- score: `clip(100 * (base_bpb - sub_bpb) / bpb_score_scale, 0, 100)` — the
  ABSOLUTE bpb gain; baseline and worse-than-baseline score 0.
  `bpb_score_scale` is a display convention that maps bpb onto 0-100, NOT a
  calibration target (DESIGN.md §8.1); `score_unbounded` stays un-clipped.
- context: EVALUATION is fixed at 8192 for every submission; the TRAINING
  context is agent-controlled via a module-level `BLOCK_SIZE` in model.py
  (power of two in [256, 8192], default 8192). Shorter buys optimizer steps and
  costs length extrapolation.

## Resource budget

- `tag: systems`, single Modal **H100**, CPU judge.
- `runtime.timeout_seconds: 21600` (long-horizon agent iteration).
- Per-submission training capped at ≤ 1 h wall-clock (`train_seconds` fixed `T` +
  `max_train_seconds` hard abort).
- Hidden judge assets: tokenized train shard, held-out val byte stream, locked
  baseline architecture, cached baseline `val_bpb` (keyed by config fingerprint).

## Anti-gaming

- Static policy gate (`harness/policy.py`): model.py only, ≤256 KB, denies
  env/network/subprocess, pretrained-weight loading, file reads, metric/data/timer
  peeking; allows `model.eval()` / `torch.compile()`.
- Dynamic guards (`harness/runner.py`): judge owns the loss (computes CE from the
  model's logits on hidden val); trained-from-scratch param-delta check; degenerate
  constant-logit check; param cap; OOM → 0. Black-box safe (no traceback/stdout leak).
- Iso-wallclock CRN: baseline + submission trained back-to-back on one GPU, same
  seed/data order, scored on the same hidden bytes.

## Validation (this branch)

Torch-free layers unit-tested and **full harness smoke-tested on CPU** (no GPU):

```bash
# torch-free: policy + scoring + fingerprint (17 assertions)
bash evaluate.sh --selftest                     # -> SELFTEST OK

# full pipeline on CPU (tiny model/budget), needs torch:
FRONTIER_NANOSLM_SMOKE=1 bash evaluate.sh reference.py
#   base_val_bpb=<b>; sub_val_bpb=<s>; abs_bpb_delta=+<gain>; score=<...>  (reference > baseline)
FRONTIER_NANOSLM_SMOKE=1 python3 evaluator.py <degenerate>   # -> guard: not trained; score 0
python3 evaluator.py <torch.load>                            # -> policy_rejected; score 0

# role split (GPU via Modal from CPU judge; direct H100 only in testing mode):
FRONTIER_NANOSLM_ROLE=final  ... evaluator.py reference.py   # fresh baseline+submission CRN pair (~2T)
FRONTIER_NANOSLM_ROLE=agent  ... evaluator.py reference.py   # trains submission only; reuses
#   fingerprint-cached baseline (note=iterative(cached-baseline)), ~T per iteration
```

Standard 2.0 CLI checks to run in the repo before merge:

```bash
uv run frontier list 2.0
uv run frontier show 2.0 nanoslm_hybrid_arch_design
python3 -m py_compile 2.0/problems/nanoslm_hybrid_arch_design/evaluator.py
```

## PENDING before ship (see DESIGN.md §3)

- **[BLOCKER] Single-H100 calibration** of the wall-clock budget `T`, the
  model-scale band, and the `val_bpb` noise floor (protocol in DESIGN.md §3).
  (`r_target` was on this list; it is now `bpb_score_scale` and is no longer a
  calibration gate — DESIGN.md §8.1.)
  All such constants are flagged `CALIBRATE` in `harness/settings.py` / `config.yaml`.
- Modal end-to-end run + deployed app name / H100 SKU confirmation (GPU path awaits
  maintainer credentials, as with `nanowm`).
- Judge-image bake-asset provenance + data license (FineWeb-Edu, dolma2 BPE);
  the held-out val byte ranges are the only hidden component.
- Decide: keep the optimizer locked (current: architecture-only) vs. expose an
  optional `configure_optimizers` hook (more autoresearch-faithful).

## Files

```
2.0/problems/nanoslm_hybrid_arch_design/
  config.yaml            # systems/H100/Modal, file submission /app/model.py
  readme                 # public task statement (agent-facing)
  evaluator.py           # evaluate() + prepare() + --selftest; torch-free top-level
  evaluate.sh            # local CLI wrapper (+ --selftest)
  reference.py           # reference solution model.py (3:1 GDN hybrid on the olmo3_190M baseline)
  DESIGN.md              # full design, calibration protocol, open items
  PR_SUMMARY.md          # this file
  harness/
    settings.py          # locked config + smoke overrides + config fingerprint (torch-free)
    policy.py            # static submission policy (torch-free)
    scoring.py           # val_bpb gain -> [0,100] (torch-free)
    model_config.py      # ModelConfig contract object (torch-free)
    data.py              # dolma2-BPE token data (synthetic fallback for smoke)
    baseline_model.py    # locked baseline transformer (score-0 reference point)
    train.py             # locked iso-wallclock training loop (harness-owned loss)
    eval_ppl.py          # held-out val_bpb eval + determinism knobs
    runner.py            # arm run + CRN pair + dynamic guards
```
