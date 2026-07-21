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
bash /app/submit.sh              # 3. enqueue for the judge
```

You do **not** train here — this container has no GPU and no torch. The judge
trains both your architecture and a locked baseline under the identical budget
and scores your **absolute bpb gain** over it, `base_bpb - sub_bpb`. Bits per
byte is the unit the literature quotes, so the gain is directly comparable to
published numbers; the constant that maps it onto 0–100 is a scaling convention,
not a target, so simply maximize the gain.

## What you submit

`/app/model.py`, defining `build_model(config)` or `class NanoSLM`, whose
`forward(idx)` returns logits `[B, T, 100278]` for `idx` of BPE token ids.

`config` gives you `vocab_size` (always **100278** — the dolma2 BPE tokenizer,
`allenai/dolma2-tokenizer`), `block_size` (the context you are **trained** at),
`eval_block_size` (the context you are **scored** at — always 8192), and
read-only hints. You control the architecture **and the training context
length**; the optimizer, data, tokenizer, evaluation context and the wall-clock
budget are fixed by the judge.

## Training context length — a real lever, with a real catch

Declare it with a module-level integer in `model.py`:

```python
BLOCK_SIZE = 2048     # power of two in [256, 8192]; omit it to train at 8192
```

Out-of-range or non-power-of-two values are rejected before training (score 0).

**Evaluation is always at 8192**, whatever you train at. So:

- shorter training context → cheaper steps → **more optimizer steps** in the
  same fixed wall-clock budget (at 8192, attention is ~78–84% of layer FLOPs, so
  this is a big effect);
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

Note the vocabulary is large: the embedding table alone is ~70M parameters at
d=704 (and the model ships it **tied**, one shared table), so how you handle it
(tying, factorizing, resizing) is part of the design problem rather than a
detail.

## The starting point

`/app/model.py` ships as the **3:1 Gated DeltaNet hybrid** from *Olmo Hybrid*:
three linear-recurrent layers per full-attention layer (25% attention), which
already beats the attention-only baseline. Your job is to push further.

The 3:1 ratio is inherited, not tuned — it is the OLMo-3 sliding-window pattern
`[4096, 4096, 4096, -1]`, and the recipe replaces exactly the sliding-window
layers with GDN. It was chosen for a sliding window, not for a linear RNN, so
there is no reason to believe it is optimal here.

The shipped model is also **parameter-matched** against the baseline the way
upstream does it (`REMOVE_HEADS`: d_model 768 -> 704, heads 12 -> 11, head_dim
64 preserved), which is why it is narrower than the shape its name suggests.

Open questions it does not answer: the ratio (3:1 vs 5:1 vs 7:1), where the
attention layers belong, recurrent state size, whether every layer should be
identical, and the rest of the block (norms, gating, MLP ratio, head count).

## Why wall-clock matters

A cheaper mixer completes more optimizer steps in the same budget, and that is
the intended lever — at ctx 8192 attention is ~78–84% of layer FLOPs. But a
slower architecture is genuinely penalized, so throughput is part of the design
problem, not an afterthought.
