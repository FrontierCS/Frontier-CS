# Design notes — dbscan_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a naive GPU DBSCAN into a fast one? The agent patches
`dbscanlib`; the judge times the patched `dbscan` against a frozen naive baseline
on hidden low-dimensional workloads and scores the geomean speedup, gated on
clustering agreement (Adjusted Rand Index). One of the four-task flashlib
kernel-optimization family (KMeans, KNN, DBSCAN, IVF-PQ), all sharing one
evaluator + one Modal GPU harness (`flash_gpu.py`).

This is a **genuine kernel task**: the core operation (radius-neighbour search +
connected components + border assignment) is not a single fast torch primitive,
so beating the naive O(N^2) baseline requires real kernel work (a bucketed/grid
radius search + fused neighbour + connected-components kernels). Contrast with
pca/svd, which were algorithmic (cov+eigh + a library eigensolver) and are not
part of this family.

## Baseline + reference

- Naive baseline (`dbscanlib/dbscan.py`, and frozen `judge/refdbscan.py`): chunked
  O(N^2) neighbour scan for the core mask, GPU label-propagation for the core
  connected components, and a smallest-core-label border rule. Verified against
  scikit-learn DBSCAN (ARI = 1.0). The border rule matches flashlib's ("smallest
  CC label among in-eps core neighbours"), so the reference agrees closely.
- Reference (`reference.patch`): vendors flashlib's optimized **Triton** planar
  grid radius-search DBSCAN (`primitives/dbscan/triton/dbscan.py` grid path +
  `kernels/flash_mst` connected components) under `dbscanlib/_kernels/…`. The
  flashlib grid kernel hard-asserts D==2 (higher D falls back to a flash_knn
  brute path), so all graded workloads are D=2 and flash_knn is stubbed out.

## Correctness gate

Adjusted Rand Index (permutation-invariant, noise-aware) between the agent's
labels and the baseline's on each iteration's fresh data, `>= ari_threshold`
(default 0.99). Judge-computed; cheat-proof (you cannot fake a high ARI without
actually reproducing the clustering). DBSCAN with fixed (eps, min_samples) is
deterministic up to border tie-breaks, which ARI absorbs.

## Workloads

Planar (D=2) planted blobs + a small uniform-noise fraction, N 100k-170k. Below
~100k the tensor-core matmul baseline (`xb @ x.t()`) beats the grid kernel's fixed
launch/grid-build overhead (H100 sweep: 100k->6x, 150k->14x, 200k->27x); the band
is chosen so the O(N^2) baseline is seconds/call (grid wins clearly) yet bounded
for `timed_iters`. `timed_iters` is 3 (vs 7 elsewhere) since each baseline call is
seconds, not ms.
Hidden workloads live in `config.yaml` (judge-only). See kmeans DESIGN for the
shared anti-hack + Modal-offload design; identical here.

## Calibration (H100 Modal trial — done)

`reference.patch` validated on H100: the vendored grid DBSCAN compiles, passes the
ARI gate with **ARI 1.0** on all six workloads, and runs
**7.2 / 12.1 / 9.5 / 18.8 / 16.6 / 21.2x** over the naive baseline (geomean
~13.3x). `speedup_target` set to 13.0. The full 6-workload judge (warmup 2 +
timed 3) completed in ~410 s, well inside `modal_timeout_seconds` (2400). Re-sweep
if the N band changes.
