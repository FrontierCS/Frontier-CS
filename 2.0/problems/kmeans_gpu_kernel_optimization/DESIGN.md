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

## Correctness gate — two gates, closes the subsample hack

The first bf16 trial exposed a **subsample reward-hack**: on random data with
`max_iters=1` and a nearest-centroid-only inertia gate, codex subsampled rows
(1/4) and feature dims (16 of 512) and returned all-zero labels — an approximate
k-means that games the tolerance while doing a fraction of the work. Two changes
close it:

1. **Planted clusters** (not random): `gen` builds `x` = well-separated blob
   centres (`centers * 6`) + unit noise. Now the assignment *matters* — a wrong
   (subsampled/low-dim) assignment lands points in the wrong blob and spikes
   inertia. Random data left inertia nearly assignment-invariant, hence hackable.
2. **Two gates** (`verdict`):
   - **Gate A — labels** (`label_tolerance = 0.02`, tight): the returned `labels`
     must be the genuine nearest-to-**init** assignment (init = the centroids the
     one-step update derives from). Checked self-referentially —
     `inertia_labeled(x, init, labels) <= (1+tol) * inertia(x, init)` — so there
     is ~0 cross-solution bf16 drift. Fake/subsampled labels inflate it (real
     1.0003x, all-zero 3.25x, 16-of-512-dim 1.24x). **This is what forces a real
     full assignment** — the "do less work" shortcut is gone.
   - **Gate B — centroids** (`inertia_tolerance = 0.05`, loose): agent
     nearest-centroid inertia `<= (1+tol) * baseline`. On planted clusters two
     bf16 one-step results drift up to ~2.8% at D=512 (boundary assignments), so
     this one is loosened; it only rejects genuinely bad centroids.

Both are permutation/convention-independent and cheat-proof. `init_centroids` are
always supplied and `tol = 0`, so the baseline is deterministic in
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

Final setup (bf16 + `max_iters=1` + planted clusters + labelled/centroid gates):
`reference.patch` (flashlib) compiles + runs on bf16 and **passes both gates on all
6 workloads**, running **2.6 / 2.1 / 6.9 / 2.6 / 12.3 / 7.1x** over the bf16 naive
baseline (geomean **4.54x**). `speedup_target = 4.5`, `label_tolerance = 0.02`,
`inertia_tolerance = 0.05`. This speedup is a *pure kernel-structure* win — both
sides bf16, precision is not a lever, and the labelled gate forces a full real
assignment so "subsample less work" is not a lever either.

(Earlier calibrations, for the record: random-data + nearest-only gate gave
geomean 4.97x but was subsample-hackable; the labelled gate vs the baseline failed
the reference at D=512 with 2.66% bf16 drift, which is why gate A is
self-referential against `init` and gate B is the loosened one.)
