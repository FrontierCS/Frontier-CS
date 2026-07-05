# Design notes — kmeans_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a naive GPU K-Means into a fast one? The agent patches
`kmeanslib`; the judge times the patched `kmeans` against a frozen naive baseline
on hidden `(N, D, K)` workloads and scores the geometric-mean speedup, gated on
clustering quality (inertia). First of a four-task **flashlib kernel-optimization
family** (KMeans, KNN, TruncatedSVD, PCA) that all share one evaluator + one
Modal GPU harness.

## Execution: Modal GPU offload (mirrors the vllm task)

The judge and the agent public test both **offload GPU work to Modal**; the
containers are light (ubuntu + `modal` + git, no torch/triton). `flash_gpu.py`
(baked at `/opt/flash_gpu.py` in both images) builds an ephemeral Modal app on a
GPU (`evaluation.gpu`, default H100), ships the frozen baseline + the patched
package **as data** (no per-submission image rebuild), runs the worker, and
returns per-workload speedups + verdicts. Needs `MODAL_TOKEN_ID` /
`MODAL_TOKEN_SECRET`. torch/triton/the vendored kernels run on the Modal image
(`evaluation.pip`).

The evaluator is generic and identical across the four tasks; only three
constants differ (`PRIMITIVE`/`PKG`/`REF_MODULE`), and all workload/threshold/
Modal values come from `config.yaml` (delivered judge-only as
`/judge/task_config.json`, never present in the agent image).

## Reference solution = best in the repo

`reference.patch` vendors flashlib's own optimized **Triton** K-Means path
(`primitives/kmeans/triton/{kmeans,assign,update}.py`) under
`kmeanslib/_kernels/…`, with imports rewritten and the string "flashlib"
scrubbed, plus a thin adapter mapping our `(N, D)` contract onto flashlib's
batched entry. It is triton-only (runs on any sm≥80), imports cleanly on CPU,
and applies + passes the patch policy. Calibrate `speedup_target` from its
measured geomean on the first GPU trial.

## Anti-reward-hack

The **load-bearing** defenses are structural, inside the GPU worker (the only
place the untrusted submission runs):

* timing primitives (`perf_counter`, `torch.cuda.synchronize`) are captured to
  locals **before** the submission is imported → monkey-patching torch cannot
  affect measurement;
* **fresh data every timed iteration** → memoizing on a repeated input is
  useless;
* quality is **re-verified from the returned tensors on every iteration** →
  returning a stale cached result for a different input is caught;
* the judge computes all metrics (no agent number is trusted);
* an ephemeral Modal container per submission → no global state persists.

The patch policy is surgical defense-in-depth (so it does not reject legitimate
vendored/optimized kernel source): only `<pkg>/**` `.py` files may change; it
bans external-optimized-library *imports* (flashlib/cuml/cupy/faiss/sklearn/
cutlass — none installed on the GPU image anyway) and process/network/
measurement-tamper patterns (`subprocess`, `socket`, `os.system`,
`torch.cuda.synchronize =`, …).

The agent-facing `readme` describes the contract, gate, scoring, and policy but
**not** how the reference is implemented.

## Correctness gate

Inertia = sum of squared L2 distances to the nearest **final** centroid, judge-
computed from the returned centroids on each iteration's data. Permutation- and
convention-independent, robust to fp drift, cheat-proof. `init_centroids` are
always supplied and `tol = 0`, so the baseline is a deterministic function of
`(x, init_centroids, max_iters)`.

## Precision lock — bf16 (task-root, not prompt)

To stop an agent from buying speed by dropping matmul precision (the earlier
codex solution picked fp16 over tf32 where the 2% inertia tolerance allowed it),
the **data is bf16**: `flash_gpu`'s `gen` returns `x` and `init_centroids` as
`bfloat16`. Because the inputs carry only bf16 precision, no solution — baseline,
reference, or agent — gains anything from fp16/tf32/fp32 (they are only slower on
bf16 data), so the only remaining lever is the kernel structure. The naive
baseline's `_assign` was switched from `torch.cdist` (which upcasts) to an
explicit **bf16 matmul** so the baseline is genuinely bf16-native too — otherwise
a trivial "use bf16 instead of the fp32 baseline" would win without kernel work.
The inertia metric itself is still computed in fp32 (upcast) so the gate is a
clean quality comparison.

## Single-iteration timing + averaging

All workloads run `max_iters = 1` (one assign + one update) so the score isolates
per-iteration kernel efficiency, not loop count. Because one call is tiny, each
workload is timed `timed_iters = 10` times on fresh data and the per-run speedups
are **averaged** (`aggregate: mean`), not median.

## Calibration (H100 Modal trial — done)

bf16 + `max_iters=1`: `reference.patch` (flashlib) compiles + runs on bf16, passes
the inertia gate with **<0.0012%** drift on all 6 workloads, and runs
**5.0 / 2.6 / 10.9 / 1.8 / 12.6 / 4.7x** over the bf16 naive baseline
(geomean **4.97x**). `speedup_target = 5.0`, `inertia_tolerance = 0.02` (huge
margin). This 5x is now a *pure kernel-structure* speedup (both sides bf16).
