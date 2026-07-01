# Design notes — pca_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a naive GPU PCA into a fast one? The agent patches `pcalib`;
the judge times the patched `pca` against a frozen naive baseline on hidden
`(N, D, k)` workloads and scores the geometric-mean speedup, gated on subspace
quality (orthonormal components + captured variance). One of a four-task
**flashlib kernel-optimization family** (KMeans, KNN, TruncatedSVD, PCA) that all
share one evaluator + one Modal GPU harness.

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

`reference.patch` vendors flashlib's own optimized **Triton** PCA path
(`primitives/pca/triton/pca.py` + the `linalg/eigh` cuSOLVER/MKL/Triton-Jacobi
stack it depends on) under `pcalib/_kernels/…`, with imports rewritten and the
string "flashlib" scrubbed, plus a thin adapter mapping our
`pca(x, n_components) -> (components, explained_variance)` contract onto
flashlib's entry (which returns eigenpairs of the small cov/Gram matrix). It is
triton-only (runs on any sm≥80), imports cleanly on CPU (kernels compile lazily),
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

Two judge-computed parts, evaluated from the *components the submission returns*
(not from any agent-provided number), on each iteration's seeded `x`:

* **Orthonormality** — `max |V Vᵀ − I|` over the returned `(k, D)` components must
  not exceed `ortho_tolerance`. Blocks returning a rank-deficient or
  non-orthonormal "subspace" to cheat the variance term.
* **Captured variance** — `(1/(N−1)) ||X_c V||_F²`, where `X_c` is the
  mean-centred data, must be at least `(1 − captured_tolerance)` of the
  baseline's captured variance.

Rotation/sign/basis-convention independent (only the spanned subspace matters),
robust to fp drift, cheat-proof: high captured variance requires actually
recovering the leading principal subspace. Data is a fixed function of
`(N, D, seed)` with seeds derived from `base_seed`, so the naive baseline is
reproducible. Note: `pca` returns `(components, explained_variance)`, so
`components` is the **first** tuple element (the worker reads `agent_out[0]` for
the subspace-quality checks).

## Calibration TODO (needs a Modal GPU trial)

- Run `reference.patch` on Modal; confirm it passes the orthonormality + captured
  variance gates on all workloads (bump `captured_tolerance` / `ortho_tolerance`
  if the low-precision matmul path drifts slightly) and set `speedup_target` from
  its geomean.
- Confirm the pinned `torch`/`triton` in `evaluation.pip` compile the vendored
  kernels, and hidden shapes fit the GPU.
- Confirm Modal token wiring in the Harbor judge/agent containers.
