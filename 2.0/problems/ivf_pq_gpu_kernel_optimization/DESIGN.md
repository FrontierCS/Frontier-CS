# Design notes — ivf_pq_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a naive GPU IVF-PQ search into a fast one? The agent patches
`ivfpqlib`; the judge builds a fixed IVF-PQ index once per workload with a frozen
builder, then times the patched `ivf_pq_search` against a frozen naive baseline
over that same index on hidden ANN workloads and scores the geomean speedup,
gated on iso-result recall@k. One of the four-task flashlib kernel-optimization
family (KMeans, KNN, DBSCAN, IVF-PQ), all sharing one evaluator + one Modal GPU
harness (`flash_gpu.py`).

This is a **genuine kernel task**: the core operation (coarse list probe + a
ragged asymmetric-distance scan of PQ codes with an on-chip top-k) is not a
single fast torch primitive. The naive baseline's per-query Python loop is the
bottleneck; beating it requires fusing the coarse probe, the per-list distance
tables, and the ragged candidate scan into GPU kernels. Contrast with pca/svd,
which were algorithmic (cov+eigh + a library eigensolver) and are not part of
this family.

## Baseline + reference

- Naive baseline (`ivfpqlib/`, and frozen `judge/refivfpq.py`): a pure-torch
  IVF-PQ. `ivf_pq_build` is a coarse Lloyd k-means quantizer + per-subspace PQ
  codebooks encoding residuals to `(M, m)` uint8 codes in CSR cell-contiguous
  layout; `ivf_pq_search` probes the `nprobe` nearest lists, builds the residual
  ADC lookup table per query, scores each probed candidate as the sum of `m`
  table lookups, and keeps the global top-`k`. The per-query Python loop is what
  makes search slow. `refivfpq.py` is the byte-identical frozen copy (verified),
  so the reference agrees with the baseline to fp tolerance.
- Reference (`reference.patch`): vendors flashlib's optimized **Triton** IVF-PQ
  fine scan (`primitives/ivf_pq/triton/{search,fine_scan,fine_scan_batch,
  fine_scan_gemm,lut}.py`) under `ivfpqlib/_kernels/…`, rewriting search's
  `ivf_pq_search`. The coarse nprobe-nearest-centroid step is done with an exact
  `torch.cdist().topk()` (flashlib routes it through `flash_knn`; over a few
  hundred centroids that is the same exact result and a negligible fraction of
  the time, so the KNN subtree is not vendored). The CuTe DSL Hopper tier is
  disabled (`is_cutedsl_available -> False`), so the portable Triton
  LUT-scan / decode+GEMM kernels run — flashlib's best non-DSL path.

## Correctness gate

Iso-result recall@k between the agent's ids and the baseline's on the **same**
index and queries each iteration, `>= recall_threshold`. Judge-computed;
cheat-proof (you cannot fake a high recall without actually reproducing the ADC
ranking). Because the index is fixed and shared, both search implementations
target the same ground truth; the reference's LUT/GEMM kernels reproduce the
naive ADC distances to fp tolerance, so recall is near 1.0 (ties on equal ADC
sums are the only source of <1.0). `recall_threshold` is set below the
reference's measured iso-recall with margin — calibrate after the GPU trial.

## Workloads

Random float32 databases, `M` 50k–150k, `D` 64–128, `nlist` 256–512, `m` 8–16,
`nprobe` 8–32, `nq` ~1k–2k. The index build (frozen, not timed) and the naive
baseline search both stay within the Modal timeout while the fused kernel gives a
large speedup. Hidden workloads live in `config.yaml` (judge-only). See kmeans
DESIGN for the shared anti-hack + Modal-offload design; identical here, plus a
`setup(w, seed)` worker hook that builds the fixed index once per workload (the
frozen builder), reused across all timed iterations while queries regenerate.

## Calibration (H100 Modal trial — done)

`reference.patch` validated on H100: the vendored Triton search compiles, passes
the recall gate with iso-recall **1.0** on all six workloads, and runs
**513 / 907 / 1420 / 1449 / 442 / 1234x** over the naive baseline (geomean
~898x). `speedup_target` set to 800 (reference scores ~100, capped);
`recall_threshold` 0.95 (well below the measured 1.0). Re-sweep if workload
sizes change. The large factors reflect the Python-per-query-loop baseline;
fully closing the gap needs the fused ragged scan, not just torch vectorization.
