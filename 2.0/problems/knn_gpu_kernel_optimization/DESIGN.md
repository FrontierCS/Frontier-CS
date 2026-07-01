# Design notes — knn_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a naive GPU brute-force k-NN into a fast one? The agent
patches `knnlib`; the judge times the patched `knn` against a frozen naive
baseline on hidden `(Q, M, D, k)` workloads and scores the geometric-mean
speedup, gated on nearest-neighbor quality (recall@k). Second of a four-task
**flashlib kernel-optimization family** (KMeans, KNN, TruncatedSVD, PCA) that
all share one evaluator + one Modal GPU harness.

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

`reference.patch` vendors flashlib's own optimized **Triton** k-NN path
(`primitives/knn/triton/{dispatch,insert,sortmerge,_common,_row_norm}.py` plus
the squared-L2 gather kernel `kernels/distance/triton/knn_gather_l2sq.py`) under
`knnlib/_kernels/…`, with imports rewritten and the string "flashlib" scrubbed,
plus a thin adapter mapping our `(Q, D)` / `(M, D)` contract onto flashlib's
batched entry (`flash_knn_triton` for the indices + `triton_knn_gather_sqdist`
for the true squared distances). It is triton-only (runs on any sm≥80), imports
cleanly on CPU, and applies + passes the patch policy. Calibrate `speedup_target`
from its measured geomean on the first GPU trial.

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

recall@k = fraction of the true `k` nearest database indices the submission
recovers, averaged over all queries, judge-computed from the returned indices on
each iteration's data against the frozen exact baseline (`refknn`, a `cdist` +
`topk`). Tie-break- and convention-independent (exact-set based), robust to fp
drift, cheat-proof: high recall requires actually finding the neighbors.
`queries`/`database` are generated from a per-workload seed, so the baseline —
and thus the true top-k — is a deterministic function of `(Q, M, D, k, seed)`.

## Calibration TODO (needs a Modal GPU trial)

- Run `reference.patch` on Modal; confirm it passes the recall@k gate on all
  workloads (bump `recall_threshold` slack only if flashlib's low-precision
  cross-term drifts a hair) and set `speedup_target` from its geomean.
- Confirm the pinned `torch`/`triton` in `evaluation.pip` compile the vendored
  kernels, and hidden shapes fit the GPU.
- Confirm Modal token wiring in the Harbor judge/agent containers.
