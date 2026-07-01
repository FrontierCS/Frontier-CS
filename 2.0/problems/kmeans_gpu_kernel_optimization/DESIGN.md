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

## Calibration TODO (needs a Modal GPU trial)

- Run `reference.patch` on Modal; confirm it passes the inertia gate on all
  workloads (bump `inertia_tolerance` if flashlib's low-precision assign drifts
  slightly) and set `speedup_target` from its geomean.
- Confirm the pinned `torch`/`triton` in `evaluation.pip` compile the vendored
  kernels, and hidden shapes fit the GPU.
- Confirm Modal token wiring in the Harbor judge/agent containers.
