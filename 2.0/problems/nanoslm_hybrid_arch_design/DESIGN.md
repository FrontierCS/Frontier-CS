# Design — nanoslm_hybrid_arch_design

## 1. Task

Design a **hybrid language-model architecture** — mixing attention with
linear-recurrent sequence mixers — that reaches the lowest held-out
**bits-per-byte (`val_bpb`)** when trained from scratch under a **fixed
wall-clock budget on a single H100**. The agent submits one file, `model.py`
(full freedom over the model definition); the hidden judge drops it into a
**locked** dolma2 BPE training + evaluation harness, trains it for a fixed
wall-clock `T`, and scores `val_bpb` against a **locked baseline architecture**
trained under the identical budget.

## 1.1 Where the starting setup comes from

The initial configuration is taken from **Olmo Hybrid: From Theory to Practice
and Back** (Merrill, Li, Romero et al., arXiv:2604.03444). That work shows
theoretically that hybrids express capabilities beyond both transformers and
linear RNNs, then validates it at 7B by replacing sliding-window attention
layers with Gated DeltaNet layers, outperforming the comparable Olmo 3 baseline.

Concretely inherited from it and from the OLMo-core implementation:

  * the **3:1 interleaved pattern** (three Gated DeltaNet layers per full
    attention layer, i.e. 25% attention), which is what `reference.py` ships as
    the agent's starting point;
  * the practice of **rebalancing head count / width so the hybrid is
    parameter-matched** against the pure-attention baseline
    (`REMOVE_HEADS` in the upstream script) — **now applied** as
    `REMOVE_HEADS = 1` (d_model 768 -> 704, n_heads 12 -> 11);
  * **dolma2** tokenization and the ~190M OLMo3 shape (d=768, L=12, H=12).

The scientific questions this task poses are the ones that paper answers at
scale but leaves open at 190M under a tight, parameter-matched, wall-clock
budget — enumerated in §1.2. The agent **builds on the baseline architecture**
(`harness/baseline_model.py`, a faithful pure-attention `olmo3_190M`) and
hybridizes it; `reference.py` ships one worked hybrid — the 3:1 GDN pattern — as
an existence proof, not a ceiling. It doubles as the repo-required reference
*solution* and the CI gate: `reference.py` must beat the hidden, score-0
`baseline_model.py` (the pure-attention `olmo3_190M`, judge-side only).

The optimizer, LR schedule, data, tokenizer, EVALUATION context (8192) and
budget are all fixed by the judge. The agent changes the architecture — and the
TRAINING context length, which trades optimizer steps against length
extrapolation.

## 1.2 The three research questions

The task is organized around the three architecture questions the Olmo Hybrid
paper settles at 7B and ablates on a 60M–1B ladder (its Table 5, `val_bpb`
averaged over Math/Code/QA; lower is better). The agent re-derives them at 190M,
**from the pure-attention baseline up**, under a fixed wall-clock budget and a
hard parameter cap — conditions under which the paper's answers are *priors, not
conclusions* (see the caveat below).

1. **RNN architecture — GDN vs. Mamba2.** Which linear-recurrent mixer makes the
   best hybrid? Paper prior @190M: Gated DeltaNet (3:1) reaches 0.891 bpb vs.
   Mamba2 (3:1) at 0.921, and pure GDN (0.895) beats pure Mamba2 (0.941). GDN is
   the paper's pick and is what `reference.py` ships; whether that margin
   survives parameter-matching at this scale is open.

2. **Layer placement — interleaved vs. concentrated.** Given a fixed count of
   attention layers, where do they go? Paper prior @190M: uniformly interleaved
   (0.891) beats concentrating them in the middle of the stack (0.899). The
   paper's argument is structural — concentrating attention forces all global
   information through one bottleneck, whereas interleaving maximizes the number
   of alternations between mixer types, which its expressivity theory (Theorems
   1 and 3) predicts should help. Clustering attention early (context in) vs.
   late (read-out) is unexplored and on the table.

3. **Attention ratio — how much attention is enough?** What fraction of layers
   should stay full attention? Paper prior @190M: 1:1 / 50% (0.896), 3:1 / 25%
   (0.891), 7:1 / 12.5% (0.892) — nearly a wash at this scale (a 0.001 bpb
   spread), with the paper selecting 3:1 because it wins at 600M–1B, not at
   190M. Fewer attention layers also buy more optimizer steps under the
   wall-clock budget (§5), so here the ratio trades context against *both*
   parameters and steps.

**Why the paper's answers are priors, not conclusions here.** The paper's 190M
hybrids are *not* parameter-matched: its GDN (3:1) carries ~254M non-embedding
params against the transformer's ~190M — **+34%** — and the paper flags exactly
this (Table 22: "per-size comparisons should be interpreted with care, as
architectures at the same nominal scale differ in actual parameter count"). This
task instead matches non-embedding params to ≈±2% (the `REMOVE_HEADS`
compensation in `reference.py`, measured at −2.19%) and enforces a hard
`param_cap`, so the portion of the paper's measured gain that was *bought with
parameters* is unavailable. The scored question is which of these three choices
still pays once the parameters are held fixed and the clock — not the token
count — is the budget.

Beyond the three headline axes, `reference.py` enumerates the finer knobs each
one interacts with: recurrent state size (`expand_v`, `num_v_heads` — cheap at
8192 since it does not grow with sequence length), non-uniform layers, and the
rest of the block (norm placement, gating, MLP ratio, head count, embedding
tying).

## 2. Metric: held-out bits-per-byte (`val_bpb`)

The tokenizer is **dolma2 BPE** (`allenai/dolma2-tokenizer`, the OLMo-3
tokenizer, vocab 100278), locked by the judge. Token-level cross-entropy is not
comparable across models unless tokenization is fixed, so the metric normalizes
it by the **raw byte count** of the held-out text rather than by tokens:
`val_bpb = (held-out token cross-entropy in bits) / (held-out bytes)`. Dividing
by bytes makes the number **tokenizer-independent and ungameable** — the agent
submits a model, not a tokenizer, so it cannot lower `val_bpb` by retokenizing,
and the metric stays comparable across architectures the way a byte-level vocab
used to make it by construction. Lower is better; §8 scores the absolute gain
over the locked baseline.

## 3. Why this is a real task

Under a fixed wall-clock budget the frontier is genuinely architectural. Because
the baseline is already a tuned `olmo3_190M`, the easy block-level wins (RMSNorm,
rotary, QK-norm, SwiGLU) are **already in it**; what is left on the table is the
hybrid direction — the mixer, ratio, placement, and state size of §1.2.

## 4. Submission surface & interface

Submission is a **single file**, `/app/model.py` (`submission.kind: file`). Only
this file travels to the judge; edits to the harness in the agent workspace are
ignored by scoring (black-box judge uses its own locked harness copies).

`model.py` must expose a factory the harness can call:

```python
def build_model(config) -> torch.nn.Module: ...
# or a class usable as NanoSLM(config)
class NanoSLM(torch.nn.Module): ...
```

`config` is the harness-owned `ModelConfig`: `vocab_size` (100278), `block_size`
(the TRAINING context, which the submission may set via a module-level
`BLOCK_SIZE`), `eval_block_size` (the SCORING context, always 8192 and never
negotiable), plus read-only budget hints. The returned module must implement:

```python
def forward(self, idx):            # idx: LongTensor [B, T] of token ids in [0, vocab_size)
    return logits                  # FloatTensor [B, T, vocab_size]
    # returning (logits, loss) is accepted, but the judge IGNORES any returned
    # loss and computes cross-entropy itself for BOTH training and val_bpb.
```

The judge owns the loss so a model cannot report a fake low loss. The optimizer,
LR schedule, weight-decay grouping (no WD on 1-D params), data order and
wall-clock budget are all locked in `harness/train.py`; the training context is
the one training-side quantity the submission controls, and the evaluation
context is locked in `harness/data.py::val_windows`.

## 5. Iso-wallclock protocol (the anti-gaming axis)

- The judge trains the baseline and the submission for the **same fixed
  wall-clock `T`** on the **same H100**, from the **same seed and data order**
  (common random numbers), then evaluates both on the **same hidden held-out
  validation set**. The scored (final/verifier) run measures baseline + submission
  back-to-back in one job/GPU/process (no cache), mirroring
  `nanowm`'s `run_pair(role="final")`. A cached baseline keyed by
  `settings.config_fingerprint()` is used only for the cheap iterative
  (agent-role) feedback path. Role is selected by the judge via
  `FRONTIER_NANOSLM_ROLE` (`agent` = train submission only + cached baseline, ~T;
  `final` = fresh baseline+submission CRN pair, ~2T; default `final`). GPU is
  served on Modal from a CPU judge; a directly-attached H100 is
  used only in local testing mode.
- The wall-clock cutoff is enforced **by the harness timer**, not by anything the
  model can influence: training stops at the first optimizer step whose start
  exceeds `T`. Model `forward` cost therefore trades directly against step count
  — a more efficient architecture legitimately completes more useful steps. This
  is the intended lever, and it is the mechanism by which a hybrid can win at
  all: at ctx 8192 attention is estimated to dominate layer FLOPs (~78–84%, an
  analytic estimate not yet confirmed on the judge GPU), so replacing most of it
  with a cheaper mixer converts directly into extra optimizer steps.
- Determinism: fixed seeds; `torch.use_deterministic_algorithms(True,
  warn_only=True)`, `cudnn.deterministic=True`, `benchmark=False`, TF32
  **disabled** during eval, `CUBLAS_WORKSPACE_CONFIG=:4096:8`. Iso-wallclock has
  irreducible timing noise (step count varies run-to-run); the CRN pairing keeps
  the *comparison* stable even so. The seed-to-seed noise floor itself is an open
  calibration item, not yet measured on the judge GPU.

## 6. Submission policy (validated before training; torch-free, unit-tested)

`model.py` only (`.py`), ≤ 256 KB, no file deletion, safe path; the submission
must define `build_model(config)` or `class NanoSLM`.

Two deny lists in `harness/policy.py`, scanned differently (representative, not
exhaustive):

- `POLICY_DENY_TOKENS`, matched over the **full source** — a leak signal in a
  comment is still a leak:
  - **Escape / leakage:** `os.environ`, `os.getenv`, `putenv`, `subprocess`,
    `socket`, `requests`, `urllib`, `httpx`, `FRONTIER_`/`JUDGE_`/`HARBOR_`/`MODAL_`,
    `HF_TOKEN`, judge paths (`/judge`, `/opt/`, `/tests/`).
  - **Pretrained-weight loading (must train from scratch):** `from_pretrained`,
    `torch.load`, `load_state_dict`, `hf_hub`, `huggingface`, `safetensors`, `AutoModel`.
  - **Filesystem reads:** `open(`, `Path(`, `np.load`, `np.fromfile`, `mmap`, `pickle.load`.
  - **Timer / control-flow / concurrency:** `time.time`, `time.perf_counter`,
    `time.sleep`, `while True`, `threading`, `multiprocessing`, `os.fork`, `ctypes`,
    `exec(`, `__import__`.
- `POLICY_DENY_TOKENS_CODE`, matched over **code only** (comments and string
  literals stripped) so a docstring *may* name the metric it targets: `val_ppl`,
  `perplexity`, `val_bpb`, `bits_per_byte`, `holdout`, `val_data`, `val.bin`.

`eval(` and `compile(` are deliberately **allowed** so `model.eval()` and
`torch.compile()` work — the sandbox and judge-owned loss cover the rest.

The policy is a **static allow/deny gate**; §7 guards the residual dynamic
risks it cannot see.

## 7. Dynamic guards (what the static scan can't catch)

- **Judge owns the loss.** `val_bpb` is computed by the harness from the model's
  `logits` via its own cross-entropy on **hidden** held-out bytes (never mounted
  in `/app`), so a model cannot report a fake loss or memorize the val set.
- **Trained-from-scratch guard.** Params are fingerprinted at init and re-checked
  after training; a model whose weights did not change (untrained / frozen
  constant) or that produces a (near-)constant logit distribution over inputs is
  scored 0. Blocks "return a cached distribution" degenerate submissions.
- **Resource caps.** Param count ≤ `PARAM_CAP` and peak activation memory within
  the H100; OOM or over-cap → score 0 with a public message (no traceback). Stops
  memory-bomb / timer-dodge attempts.
- **Sandboxing.** Submitted code is imported and run as an unprivileged user with
  the evaluator source chmod-protected (same pattern as `erdos_demo`); evaluator
  output returns public metrics and concise errors only — never raw submission
  stdout/stderr or tracebacks (2.0 black-box safety rules).

## 8. Scoring — ABSOLUTE bits-per-byte gain

`harness/scoring.py` (shared with the public test). Lower `val_bpb` is better.
With `base_bpb` = locked-baseline held-out bits-per-byte and `sub_bpb` = the
submission's, both trained under the identical wall-clock budget with common
random numbers and both evaluated at the fixed 8192-token window:

```
gain  = base_bpb - sub_bpb                        # THE MEASUREMENT
score = clip(100 * gain / bpb_score_scale, 0, 100)
```

Baseline-tying and worse-than-baseline both score 0. `score_unbounded` is the
un-clipped ratio and keeps rising past 100.

### 8.1 `bpb_score_scale` is a display convention, NOT a calibration target

The only measurement is `gain`, in bits per byte. `bpb_score_scale` exists solely
to map that gain onto the 0–100 range Harbor's `reward = score / 100` expects — a
raw gain of 0.05 bpb would otherwise surface as reward 0.0005. It is **not** a
calibrated definition of "a full win": no such number has been measured, and the
clip discards information (a submission at 2× the scale scores the same 100 as one
exactly at it), which is why `score_unbounded` stays un-clipped for an operator to
read.

The one real requirement is **discrimination**: too large and everything pins at
0, too small and everything pins at 100 — checkable from a single real-corpus run,
no headroom study needed. Current value: `bpb_score_scale = 0.05` bpb. (The
predecessor `r_target` is dropped, not satisfied: it asked for a measured full-win
definition that was never well-posed.)

## 9. Compute / infra

- `tag: systems`; H100 served on Modal (one per environment), CPU judge —
  identical shape to `nanowm_rollout_speedup` and `vllm_llm_serving_optimization`.
- `runtime.timeout_seconds`: long-horizon (agent iterates for hours);
  per-submission training is capped at ≤ 1 h/train (single H100).
- Hidden judge assets (judge image only): the tokenized training shard, the
  **held-out** validation byte stream, the locked baseline architecture, and the
  cached baseline `val_bpb` (keyed by config fingerprint). None are mounted in
  `/app`.