# Design notes — truncated_svd_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a correct-but-naive GPU truncated SVD into a fast one? The
agent is given `tsvdlib` (a `torch.linalg.svd` full-SVD call that then slices the
top-k factors) and must rewrite the internals — ideally a Gram-matrix `X^T X`
followed by a top-k eigendecomposition (`torch.linalg.eigh`), plus fused kernels
— to maximize the geometric-mean speedup over the frozen baseline across a family
of hidden `(N, D, k)` workloads, subject to an approximation-quality gate.

This is the third of a four-task **flashlib kernel-optimization family**
(KMeans, KNN, TruncatedSVD, PCA). All four share the KernelBench-style pattern:
ship a naive package, freeze a byte-for-byte baseline in the judge image, apply
the agent's patch to a clean copy, time patched-vs-baseline on identical seeded
data in an isolated worker, and gate on a primitive-appropriate quality metric
before scoring by geomean speedup. PCA is the sibling task: it is the same
Gram/eig idea but on the **covariance** matrix (mean-centre `X` first, then the
right singular vectors of the centred matrix are the principal directions), so
the PCA gate additionally has to account for the centering step.

## Correctness gate: orthonormality + captured energy, judge-computed

The SVD has sign and rotation ambiguities (any singular vector may be negated,
and vectors spanning equal singular values may be rotated within their
eigenspace), so an elementwise comparison against the baseline's factors is
meaningless. Instead the judge worker checks two rotation/sign-invariant
properties of the returned `components` `V` (shape `(k, D)`), computed from what
the submission returns (not from any agent-provided number), on the same seeded
`x` used for the baseline:

- **Orthonormality**: `max |V V^T - I_k| <= ortho_tolerance` (default 2%). The
  rows must be an orthonormal basis of a k-dimensional subspace.
- **Captured energy**: `||X V^T||_F^2 >= (1 - captured_tolerance)` times the
  baseline's captured energy (default 2%). This is the squared Frobenius norm of
  the projection of the data onto the returned subspace — the quantity truncated
  SVD is supposed to maximise (Eckart–Young). It depends only on the *subspace*
  spanned by the rows of `V`, so it is invariant to sign flips and to any
  in-subspace rotation.

Properties:

- rotation/sign-convention independent (only the spanned subspace matters);
- robust to floating-point drift;
- cheat-proof: you cannot return fast garbage — high captured energy requires
  actually recovering the leading right-singular subspace, and the orthonormality
  gate blocks degenerate `V` (e.g. repeated or unnormalised rows) that could
  otherwise inflate the projected energy. Trading some numeric precision for
  speed (tf32/bf16 accumulation in the Gram GEMM) is allowed within tolerance.

`singular_values` are still required by the shape/finiteness check but are not
part of the quality gate; the captured-energy formulation makes the gate depend
on the subspace, which is what a downstream user of a truncated SVD cares about.

Determinism: `x` is drawn from a fixed seeded generator per workload (seeds
derived from `base_seed`), so the baseline result is a fixed function of `(N, D,
k, seed)`.

## Anti-gaming

flashlib (the library these primitives are distilled from) is public and
Apache-2.0. Mitigations:

- The shipped package is a small, neutrally named library (`tsvdlib`), not
  flashlib; the patch allowlist confines edits to `tsvdlib/**`.
- The patch policy forbids importing `flashlib`/cuML/cuPy/FAISS/scikit-learn and
  bans env/subprocess/network access — the agent must write the kernels itself.
- Scored shapes are hidden and differ from the two public shapes; seeds derive
  from `base_seed`. General kernels win; shape lookups do not.
- The gate is a subspace-quality metric, not an elementwise factor match, so an
  agent cannot "pass" by copying baseline numbers — it must produce a genuinely
  good rank-k approximation.
- Honest framing: reproducing SOTA-class kernels *is* the bar. We block trivial
  library reuse, not the underlying knowledge.

## Execution model & the Modal question

The evaluator runs an isolated worker subprocess (`_run_worker`) that imports the
frozen baseline (`/opt/tsvd_ref/reftsvd.py`) and the patched `tsvdlib` (from the
applied clean tree), times both, and reports JSON. This assumes the **judge
container has a GPU**.

The repo's other GPU task (vllm) instead offloads to **Modal** because Harbor
judge containers may not be GPU-scheduled. `_run_worker` is the single swap
point: to go Modal, replace it with a Modal function that builds the patched
package, runs the same worker logic on a Modal GPU, and returns the JSON rows.
The rest of the evaluator (policy, gating, scoring) is unchanged. Decide
in-container-GPU vs Modal at first calibration trial.

## Calibration TODO (needs a GPU trial)

- Validate `reference.patch` (Gram + `eigh`) runs and passes the orthonormality
  and captured-energy gates on all workloads; fix any torch API drift for the
  pinned torch in the image.
- Measure the reference solution's geomean speedup and set `speedup_target` so a
  reference-level solution maps to ~full score.
- Confirm hidden shapes fit device memory (the naive baseline's full
  `torch.linalg.svd` on the `N x D` matrix is the memory driver; all shipped
  shapes are H100-safe, and the Gram-matrix reference is far lighter since it
  only decomposes the `D x D` matrix).
- Sanity-check timing stability (median-of-7); bump `timed_iters` if noisy.

## Files

- `tsvdlib/` — pristine package baked into both images (agent edits it).
- `judge/reftsvd.py` — frozen baseline, baked to `/opt/tsvd_ref/`.
- `evaluator.py` — self-contained policy + orchestration + scoring (judge-only).
- `reference.patch` — Gram-matrix + eigh reference solution (proves solvability).
- `docker/` — builds the prebuilt agent/judge images referenced by config.yaml.
- `harbor/app/` — agent-facing submission helpers + public self-test.
