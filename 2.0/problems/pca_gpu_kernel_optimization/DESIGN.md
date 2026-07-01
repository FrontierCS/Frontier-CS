# Design notes — pca_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a correct-but-naive GPU PCA into a fast one? The agent is
given `pcalib` (a full-SVD-on-the-centred-matrix implementation) and must
rewrite the internals — ideally a covariance/Gram matrix (`Xᵀ X`, one GEMM)
followed by a top-`k` symmetric eigendecomposition, with fused centring and no
materialization of the centred data — to maximize the geometric-mean speedup
over the frozen baseline across a family of hidden `(N, D, k)` workloads,
subject to a subspace-quality gate.

This is the fourth of a four-task **flashlib kernel-optimization family**
(KMeans, KNN, TruncatedSVD, PCA). All four share the KernelBench-style pattern:
ship a naive package, freeze a byte-for-byte baseline in the judge image, apply
the agent's patch to a clean copy, time patched-vs-baseline on identical seeded
data in an isolated worker, and gate on a primitive-appropriate quality metric
before scoring by geomean speedup. TruncatedSVD is the sibling primitive: it
factors the raw data matrix directly (no mean-centring), whereas PCA here is
covariance-based and centres by the feature mean.

## Correctness gate: orthonormality + captured variance, judge-computed

The quality gate has two judge-computed parts, evaluated from the *components
the submission returns* (not from any agent-provided number), on the same seeded
`x` used for the baseline:

- **Orthonormality** — `max |V Vᵀ − I|` over the returned `(k, D)` components
  must not exceed `ortho_tolerance` (default 2%). This forbids returning a
  rank-deficient or non-orthonormal "subspace" to cheat the variance term.
- **Captured variance** — `(1/(N−1)) ||X_c V||_F²`, where `X_c` is the
  mean-centred data, must be at least `(1 − captured_tolerance)` (default 2%) of
  the baseline's captured variance. The centring uses the feature mean of `x`.

Properties:

- rotation/sign/basis-convention independent — only the *subspace* spanned by
  the components matters, so the gate does not care whether the agent returns
  eigenvectors in a different sign or rotated within the top-`k` subspace;
- robust to floating-point drift across the eigendecomposition;
- cheat-proof: you cannot return fast garbage — high captured variance requires
  actually recovering the leading principal subspace, and the orthonormality
  check blocks degenerate answers. Trading some numeric precision for speed
  (tf32/bf16 accumulation in the GEMM) is allowed within tolerance.

Determinism: data is a fixed function of `(N, D, seed)`; seeds derive from
`base_seed`. The naive baseline result is therefore reproducible.

Note on the worker: `pca` returns `(components, explained_variance)`, so
`components` is the **first** element of the tuple (unlike the SVD sibling where
the singular values come first). The worker reads `agent_out[0]` for the
subspace-quality checks.

## Anti-gaming

flashlib (the library these primitives are distilled from) is public and
Apache-2.0. Mitigations:

- The shipped package is a small, neutrally named library (`pcalib`), not
  flashlib; the patch allowlist confines edits to `pcalib/**`.
- The patch policy forbids importing `flashlib`/cuML/cuPy/FAISS/scikit-learn and
  bans env/subprocess/network access — the agent must write the kernels itself.
- Scored shapes are hidden and differ from the two public shapes; seeds derive
  from `base_seed`. General kernels win; shape lookups do not.
- Honest framing: reproducing SOTA-class kernels *is* the bar. We block trivial
  library reuse, not the underlying knowledge.

## Execution model & the Modal question

The evaluator runs an isolated worker subprocess (`_run_worker`) that imports the
frozen baseline (`/opt/pca_ref/refpca.py`) and the patched `pcalib` (from the
applied clean tree), times both, and reports JSON. This assumes the **judge
container has a GPU**.

The repo's other GPU task (vllm) instead offloads to **Modal** because Harbor
judge containers may not be GPU-scheduled. `_run_worker` is the single swap
point: to go Modal, replace it with a Modal function that builds the patched
package, runs the same worker logic on a Modal GPU, and returns the JSON rows.
The rest of the evaluator (policy, gating, scoring) is unchanged. Decide
in-container-GPU vs Modal at first calibration trial.

## Calibration TODO (needs a GPU trial)

- Validate `reference.patch` runs and passes the orthonormality + captured
  variance gates on all workloads; fix any `torch.linalg.eigh` API drift for the
  pinned torch in the image.
- Measure the reference solution's geomean speedup and set `speedup_target` so a
  reference-level solution maps to ~full score (default seeded at 4.0 for the
  covariance-vs-full-SVD swap; recalibrate).
- Confirm hidden shapes fit device memory (the naive baseline materializes the
  `(N, D)` centred matrix and runs a full thin SVD; all shipped shapes are
  H100-safe).
- Sanity-check timing stability (median-of-7); bump `timed_iters` if noisy.

## Files

- `pcalib/` — pristine package baked into both images (agent edits it).
- `judge/refpca.py` — frozen baseline, baked to `/opt/pca_ref/`.
- `evaluator.py` — self-contained policy + orchestration + scoring (judge-only).
- `reference.patch` — covariance + eigh reference solution (proves solvability).
- `docker/` — builds the prebuilt agent/judge images referenced by config.yaml.
- `harbor/app/` — agent-facing submission helpers + public self-test.
