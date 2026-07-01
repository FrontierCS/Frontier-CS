# Design notes — kmeans_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a correct-but-naive GPU K-Means into a fast one? The agent is
given `kmeanslib` (a `torch.cdist`-per-iteration Lloyd loop) and must rewrite the
internals — ideally a fused Triton assignment kernel plus a better centroid
update — to maximize the geometric-mean speedup over the frozen baseline across a
family of hidden `(N, D, K)` workloads, subject to a clustering-quality gate.

This is the first of a four-task **flashlib kernel-optimization family**
(KMeans, KNN, TruncatedSVD, PCA). All four share the KernelBench-style pattern:
ship a naive package, freeze a byte-for-byte baseline in the judge image, apply
the agent's patch to a clean copy, time patched-vs-baseline on identical seeded
data in an isolated worker, and gate on a primitive-appropriate quality metric
before scoring by geomean speedup.

## Correctness gate: inertia, judge-computed

The quality gate is the k-means objective — inertia = sum over points of the
squared L2 distance to the nearest **final** centroid. It is computed by the
judge worker from the *centroids the submission returns* (not from any
agent-provided number), on the same seeded `x` and `init_centroids` used for the
baseline. Properties:

- permutation/label-convention independent (only the centroids matter);
- robust to floating-point drift across iterations;
- cheat-proof: you cannot return fast garbage — low inertia requires actually
  clustering well. Trading some numeric precision for speed (bf16/tf32
  accumulation) is allowed within `inertia_tolerance` (default 2%).

Determinism: `init_centroids` are always supplied and `tol = 0` (every iteration
runs), so the baseline result is a fixed function of `(x, init_centroids,
max_iters)`.

## Anti-gaming

flashlib (the library these primitives are distilled from) is public and
Apache-2.0. Mitigations:

- The shipped package is a small, neutrally named library (`kmeanslib`), not
  flashlib; the patch allowlist confines edits to `kmeanslib/**`.
- The patch policy forbids importing `flashlib`/cuML/cuPy/FAISS/scikit-learn and
  bans env/subprocess/network access — the agent must write the kernels itself.
- Scored shapes are hidden and differ from the two public shapes; seeds derive
  from `base_seed`. General kernels win; shape lookups do not.
- Honest framing: reproducing SOTA-class kernels *is* the bar. We block trivial
  library reuse, not the underlying knowledge.

## Execution model & the Modal question

The evaluator runs an isolated worker subprocess (`_run_worker`) that imports the
frozen baseline (`/opt/kmeans_ref/refkmeans.py`) and the patched `kmeanslib`
(from the applied clean tree), times both, and reports JSON. This assumes the
**judge container has a GPU**.

The repo's other GPU task (vllm) instead offloads to **Modal** because Harbor
judge containers may not be GPU-scheduled. `_run_worker` is the single swap
point: to go Modal, replace it with a Modal function that builds the patched
package, runs the same worker logic on a Modal GPU, and returns the JSON rows.
The rest of the evaluator (policy, gating, scoring) is unchanged. Decide
in-container-GPU vs Modal at first calibration trial.

## Calibration TODO (needs a GPU trial)

- Validate `reference.patch` runs and passes the inertia gate on all workloads;
  fix any Triton API drift (`tl.dot(input_precision=...)`, `tl.argmin`) for the
  pinned torch/triton in the image.
- Measure the reference solution's geomean speedup and set `speedup_target` so a
  reference-level solution maps to ~full score.
- Confirm hidden shapes fit device memory (the naive baseline's `cdist`
  materializes `N x K`; all shipped shapes are H100-safe).
- Sanity-check timing stability (median-of-7); bump `timed_iters` if noisy.

## Files

- `kmeanslib/` — pristine package baked into both images (agent edits it).
- `judge/refkmeans.py` — frozen baseline, baked to `/opt/kmeans_ref/`.
- `evaluator.py` — self-contained policy + orchestration + scoring (judge-only).
- `reference.patch` — fused-Triton reference solution (proves solvability).
- `docker/` — builds the prebuilt agent/judge images referenced by config.yaml.
- `harbor/app/` — agent-facing submission helpers + public self-test.
