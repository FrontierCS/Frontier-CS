# NanoSLM Hybrid Architecture Design — workspace

Design an architecture that reaches the lowest held-out **bits-per-byte** when
trained from scratch under a **fixed wall-clock budget** on one H100.

The metric is bits per **byte** of held-out text, not per token: the judge
divides your total cross-entropy by the byte length of the validation text, so
it does not depend on how many bytes a token happens to cover.

## Loop

```bash
vim /app/model.py                # 1. edit your architecture
bash /app/public_test.sh         # 2. static gate (seconds, no GPU)
bash /app/submit.sh              # 3. enqueue for the judge (returns immediately)
```

Submissions are **asynchronous**: `submit.sh` returns a UUID at once and a
scored result takes ~20 minutes of wall-clock (queue slot + warmup + the
15-minute training run + eval). Submit an initial plausible design early, then
**keep designing your next candidate while the judge works** — check results
with `bash /app/submissions.sh` / `bash /app/wait_submission.sh <uuid>`, and
`bash /app/cancel_submission.sh <uuid>` a queued or running submission you have
already superseded. The queue holds 2 submissions; don't flood it.

You do **not** train here — this container has no GPU and no torch. The judge
trains your architecture for a fixed wall-clock budget of **15 minutes (900 s)**
on one H100 — the LR cosine spans a 6-hour horizon (your run is the prefix of a
long schedule) and **kernel** warmup (Triton autotune) is outside the budget
(the 100-step LR warmup is inside); expect ~260-330 optimizer steps for
reference-class models at ctx 8192 — and scores it as
**`100 * 2**(-GAMMA * sub_bpb)` — a smooth tempered per-byte likelihood: the
curve reaches 100 exactly at 0 bpb (a perfect fit; measurements at or below
the 0.4 leakage floor are rejected instead), the reference solution scores
exactly 70, and there is no interior clipping (the [0, 100] clamp never binds
for a real measurement). HIGHER IS BETTER** (the score halves
every ~3.0 bpb). A locked baseline is trained under the identical budget and
its bpb and your gain over it are reported for context only. Failed or
rejected runs score 0. `val_bpb` is always reported alongside, comparable to
published numbers.

## What you submit

`/app/model.py`, defining `build_model(config)` or `class NanoSLM`, whose
`forward(idx)` returns logits `[B, T, 100352]` for `idx` of BPE token ids.

`config` gives you `vocab_size` (always **100352** — the dolma2 BPE tokenizer
`allenai/dolma2-tokenizer`, whose 100278 real ids are padded up, the Olmo 3
convention; actual ids stay `< 100278` but your logits must span the padded
width), `block_size` (the context you are **trained** at),
`eval_block_size` (the context you are **scored** at — always 8192), and
read-only hints. You control the architecture **and the training context
length**; the optimizer, data, tokenizer, evaluation context and the wall-clock
budget are fixed by the judge.

The static gate (`bash /app/public_test.sh` runs the judge's exact rules) is
strict: imports are limited to an allowlist — `torch`, `numpy`, `fla`,
`einops`, `triton` (custom kernels are fair game), `math` and a few
pure-computation stdlib modules — and dynamic-access primitives (bare
`eval`/`exec`/`getattr`/`__import__`/`open`, wildcard imports, dunder
attributes other than `__init__`/`__version__`/`__name__`) are rejected. `model.eval()`
and `torch.compile(...)` are fine. Run the gate locally before submitting;
its rejection reasons are exact.

## Training context length — a real lever, with a real catch

Declare it with a module-level integer in `model.py`:

```python
BLOCK_SIZE = 2048     # power of two in [256, 8192]; omit it to train at 8192
```

Out-of-range or non-power-of-two values are rejected before training (score 0).

**Evaluation is always at 8192**, whatever you train at. So:

- shorter training context → cheaper steps → **more optimizer steps** in the
  same fixed wall-clock budget (at 8192, attention is ~78–84% of layer FLOPs, so
  this is a big effect) — but at the fixed 2×16 micro-batching, halving context
  also halves tokens/step, and context-independent per-step costs mean steps do
  NOT rise proportionally: measure the trade, don't assume it;
- but you are still scored on 8192-token windows, so a model trained at 1024 has
  to produce sensible logits **8x past** any position it ever saw.

That second half depends heavily on your **position encoding**, which is a
different thing from architectural quality under a compute budget: plain RoPE
degrades sharply beyond its training length, while NTK-aware/YaRN scaling,
position interpolation and ALiBi extrapolate far better. Choosing a scheme that
survives the gap is now part of the design problem — do not shorten the context
without addressing it.

Also: anything you size off `config.block_size` (RoPE tables, learned positional
embeddings, mask buffers) must still run at `config.eval_block_size`. Size them
against `eval_block_size`, or build them lazily from the actual `T`.

The baseline always trains at 8192, so you are trading against a fixed point.

Note the vocabulary is large: the embedding table alone is ~77M parameters at
d=768 (and the model ships it **tied**, one shared table), so how you handle it
(tying, factorizing, resizing) is part of the design problem rather than a
detail.

## The starting point

`/app/model.py` ships as a **3:1 Gated DeltaNet hybrid** (following *Olmo Hybrid*,
arXiv:2604.03444): three linear-recurrent layers per full-attention layer (25%
attention), which already beats the attention-only baseline. Your job is to push
further.

The 3:1 ratio is inherited, not tuned — it is the OLMo-3 sliding-window pattern
`[4096, 4096, 4096, -1]`, and the recipe replaces exactly the sliding-window
layers with GDN. It was chosen for a sliding window, not for a linear RNN, so
there is no reason to believe it is optimal here.

The shipped model is **not parameter-matched** to the baseline: it keeps the
baseline's shape (d=768, 12 heads, 12 layers) and lets the GDN mixer's wide
recurrent state run at its natural, larger size (~254M vs the baseline's
~190M). Capacity is bounded by the hard parameter cap, not by an artificial
per-arm match — how you spend the budget under that cap is yours to decide.

Open questions it does not answer: the ratio (3:1 vs 5:1 vs 7:1), where the
attention layers belong, recurrent state size, whether every layer should be
identical, and the rest of the block (norms, gating, MLP ratio, head count).

## Why wall-clock matters

A cheaper mixer completes more optimizer steps in the same budget, and that is
the intended lever — at ctx 8192 attention is ~78–84% of layer FLOPs. But a
slower architecture is genuinely penalized, so throughput is part of the design
problem, not an afterthought.
