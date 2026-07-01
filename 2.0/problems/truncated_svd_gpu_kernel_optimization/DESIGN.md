# Design notes — truncated_svd_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a naive GPU truncated SVD into a fast one? The agent patches
`tsvdlib`; the judge times the patched `truncated_svd` against a frozen naive
baseline on hidden `(N, D, k)` workloads and scores the geometric-mean speedup,
gated on low-rank-factorization quality (orthonormal components + captured
energy). Third of a four-task **flashlib kernel-optimization family** (KMeans,
KNN, TruncatedSVD, PCA) that all share one evaluator + one Modal GPU harness.

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

`reference.patch` vendors flashlib's own optimized **Triton** truncated-SVD path
(`primitives/truncated_svd/triton/svd.py` plus the `linalg/eigh` stack it calls)
under `tsvdlib/_kernels/…`, with imports rewritten and the string "flashlib"
scrubbed, plus a thin adapter mapping our `(N, D)` contract onto flashlib's
entry. It is triton-only (runs on any sm≥80), imports cleanly on CPU, and applies
+ passes the patch policy. Calibrate `speedup_target` from its measured geomean
on the first GPU trial.

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
**not** how the reference is implemented (no Gram/eigh/avoid-full-SVD hints).

## Correctness gate

The SVD has sign and rotation ambiguities (any singular vector may be negated,
and vectors spanning equal singular values may be rotated within their
eigenspace), so an elementwise comparison against the baseline's factors is
meaningless. The judge worker instead checks two rotation/sign-invariant
properties of the returned `components` `V` (shape `(k, D)`), computed from what
the submission returns, on each iteration's data:

* **Orthonormality**: `max |V V^T - I_k| <= ortho_tolerance` (default 2%).
* **Captured energy**: `||X V^T||_F^2 >= (1 - captured_tolerance)` times the
  baseline's captured energy (default 2%) — the squared Frobenius norm of the
  projection of the data onto the returned subspace, the quantity truncated SVD
  maximises (Eckart–Young). It depends only on the *subspace* spanned by the rows
  of `V`, so it is invariant to sign flips and in-subspace rotation.

`singular_values` are required by the shape/finiteness check but are not part of
the quality gate. Determinism: `x` is drawn from a fixed seeded generator per
workload (seeds derived from `base_seed`), so the baseline result is a fixed
function of `(N, D, k, seed)`.

## Calibration TODO (needs a Modal GPU trial)

- Run `reference.patch` on Modal; confirm it passes the orthonormality +
  captured-energy gates on all workloads (bump the tolerances if flashlib's
  low-precision path drifts slightly) and set `speedup_target` from its geomean.
- Confirm the pinned `torch`/`triton` in `evaluation.pip` compile the vendored
  kernels, and hidden shapes fit the GPU.
- Confirm Modal token wiring in the Harbor judge/agent containers.
