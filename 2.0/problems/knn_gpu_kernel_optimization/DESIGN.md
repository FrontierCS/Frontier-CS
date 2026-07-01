# Design notes — knn_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a correct-but-naive GPU brute-force k-NN into a fast one? The
agent is given `knnlib` (a `torch.cdist`-then-`topk` search that materializes the
full `(Q, M)` distance matrix) and must rewrite the internals — ideally a
fused/streamed running top-k that tiles over the database and never writes the
`(Q, M)` matrix to HBM, with Triton kernels for the distance/selection passes —
to maximize the geometric-mean speedup over the frozen baseline across a family
of hidden `(Q, M, D, k)` workloads, subject to a recall@k quality gate.

This is task **2 of a four-task flashlib kernel-optimization family** (KMeans,
KNN, TruncatedSVD, PCA). All four share the KernelBench-style pattern: ship a
naive package, freeze a byte-for-byte baseline in the judge image, apply the
agent's patch to a clean copy, time patched-vs-baseline on identical seeded data
in an isolated worker, and gate on a primitive-appropriate quality metric before
scoring by geomean speedup.

## Correctness gate: recall@k, judge-computed

The quality gate is recall@k — for each query, the fraction of the true `k`
nearest database indices the submission recovers, averaged over all queries. The
true top-k is recomputed by the judge worker from the *frozen exact baseline*
(`refknn`, a `cdist` + `topk`) on the same seeded `queries`/`database`, not from
any agent-provided number. Properties:

- exact-set based, so it is robust to tie-breaking and floating-point drift in
  the distances (a neighbour at the same distance still counts as a hit only if
  its index matches the exact set — with continuous random data exact ties have
  measure zero, so a correct fast kernel scores ~1.0);
- cheat-proof: you cannot return fast garbage — high recall@k requires actually
  finding the nearest neighbours. Trading some numeric precision for speed
  (bf16/tf32 accumulation in the distance pass) is allowed as long as recall
  stays at or above `recall_threshold` (default 0.99).

Determinism: `queries` and `database` are generated from a per-workload seed
derived from `base_seed`, so the baseline result — and thus the true top-k — is
a fixed function of `(Q, M, D, k, seed)`.

## Anti-gaming

flashlib (the library these primitives are distilled from) is public and
Apache-2.0. Mitigations:

- The shipped package is a small, neutrally named library (`knnlib`), not
  flashlib; the patch allowlist confines edits to `knnlib/**`.
- The patch policy forbids importing `flashlib`/cuML/cuPy/FAISS/scikit-learn and
  bans env/subprocess/network access — the agent must write the kernels itself.
- Scored shapes are hidden and differ from the two public shapes; seeds derive
  from `base_seed`. General kernels win; shape lookups do not.
- Honest framing: reproducing SOTA-class kernels *is* the bar. We block trivial
  library reuse, not the underlying knowledge.

## Execution model & the Modal question

The evaluator runs an isolated worker subprocess (`_run_worker`) that imports the
frozen baseline (`/opt/knn_ref/refknn.py`) and the patched `knnlib` (from the
applied clean tree), times both, and reports JSON. This assumes the **judge
container has a GPU**.

The repo's other GPU task (vllm) instead offloads to **Modal** because Harbor
judge containers may not be GPU-scheduled. `_run_worker` is the single swap
point: to go Modal, replace it with a Modal function that builds the patched
package, runs the same worker logic on a Modal GPU, and returns the JSON rows.
The rest of the evaluator (policy, gating, scoring) is unchanged. Decide
in-container-GPU vs Modal at first calibration trial.

## Calibration TODO (needs a GPU trial)

- Validate `reference.patch` runs and passes the recall@k gate on all workloads;
  fix any Triton API drift for the pinned torch/triton in the image.
- Measure the reference solution's geomean speedup and set `speedup_target` so a
  reference-level solution maps to ~full score.
- Confirm hidden shapes fit device memory (the naive baseline's `cdist`
  materializes the full `Q x M` matrix; all shipped shapes are H100-safe, and
  the chunked reference never materializes it).
- Sanity-check timing stability (median-of-7); bump `timed_iters` if noisy.

## Files

- `knnlib/` — pristine package baked into both images (agent edits it).
- `judge/refknn.py` — frozen exact baseline, baked to `/opt/knn_ref/`.
- `evaluator.py` — self-contained policy + orchestration + scoring (judge-only).
- `reference.patch` — chunked running-top-k reference solution (proves solvability).
- `docker/` — builds the prebuilt agent/judge images referenced by config.yaml.
- `harbor/app/` — agent-facing submission helpers + public self-test.
