# Design notes — kmeans_gpu_kernel_optimization

Operator-facing. Not copied into the agent workspace by the adapter.

## What this task measures

Can an agent turn a naive GPU K-Means into a fast one? The agent patches
`kmeanslib`, whose public entry point is **one Lloyd iteration**
`step(x, centroids) -> (labels, new_centroids)`. **The judge owns the loop**: it
fixes the data + initial centroids and calls `step` a fixed number of times
(`max_iters`, feeding each output into the next), times the patched `step`
against a frozen naive baseline on hidden `(N, D, K)` workloads, and scores the
geometric-mean speedup, gated on clustering quality (inertia of the final
centroids). First of a four-task **flashlib kernel-optimization family** (KMeans,
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

`reference.patch` vendors flashlib's own optimized **Triton** K-Means path
(`primitives/kmeans/triton/{kmeans,assign,update}.py`) under
`kmeanslib/_kernels/…`, with imports rewritten and the string "flashlib"
scrubbed, plus a thin adapter mapping our `step(x, centroids)` contract onto
flashlib's single-iteration path (`_euclid_iter`: `euclid_assign_triton` +
`triton_centroid_update_sorted_euclid`, run once with the batch dim as `B=1`).
It is triton-only (runs on any sm≥80), imports cleanly on CPU, and applies +
passes the patch policy. Calibrate `speedup_target` from its measured geomean on
the first GPU trial. (The reference does not fuse assign+update into a single
kernel, so an agent that does can legitimately score >100.)

## Anti-reward-hack

The **primary, load-bearing** defense is the **`step` contract itself**: the
agent owns only one Lloyd iteration `step(x, centroids)`; the judge owns the
loop, the data, the initial centroids, and the iteration count. This structurally
closes the reward-hacks earlier trials found when the agent owned the whole
`kmeans(...)` call:

* **iteration-skip** — the agent used to run fewer than `max_iters` iterations
  and self-report the count; now the judge does the counting (`for _ in
  range(max_iters): lab, c = mod.step(x, c)`), so the count is not the agent's to
  fake;
* **fake / subsampled labels** — the judge re-derives inertia from the *final
  centroids after its own loop*; a `step` that returns garbage labels or
  subsamples rows/dims produces bad centroids that compound over the loop and
  spike inertia. `max_iters = 2` (not 1) makes it a genuine loop where a bad step
  actually propagates, while still being too few for a converged step to degrade
  into a no-op;
* **precision** — data is bf16 (locked in `gen`), so fp16/tf32/fp32 buy nothing.

Additional structural defenses inside the GPU worker (the only place the
untrusted submission runs):

* timing primitives (`perf_counter`, `torch.cuda.synchronize`) are captured to
  locals **before** the submission is imported → monkey-patching torch cannot
  affect measurement;
* quality is **re-verified by the judge from the returned tensors** → no agent
  number is trusted;
* an ephemeral Modal container per submission → no global state persists.

The patch policy is surgical defense-in-depth (so it does not reject legitimate
vendored/optimized kernel source): only `<pkg>/**` `.py` files may change; it
bans external-optimized-library *imports* (flashlib/cuml/cupy/faiss/sklearn/
cutlass — none installed on the GPU image anyway) and process/network/
measurement-tamper patterns (`subprocess`, `socket`, `os.system`,
`torch.cuda.synchronize =`, …).

The agent-facing `readme` describes the contract, gate, scoring, and policy but
**not** how the reference is implemented.

## Correctness gate — centroid inertia (the step contract does the rest)

Under the `step` contract the earlier subsample / fake-label hacks are closed
**structurally** (the judge owns the loop and re-derives quality from the final
centroids — see Anti-reward-hack), so the separate tight *label* gate is no
longer needed. One gate remains:

* **Planted clusters** (not random): `gen` builds `x` = well-separated blob
  centres (`centers * 6`) + unit noise. This makes the assignment *matter* — a
  step that assigns points to the wrong blob lands the final centroids in the
  wrong place and spikes inertia. (Random data leaves inertia nearly
  assignment-invariant, which is why it was hackable.)
* **Centroid inertia gate** (`inertia_tolerance`, recalibrate): after the judge's
  loop, the agent's final centroids' nearest-centroid inertia must be
  `<= (1+tol) * baseline`. Computed in fp32 (upcast) on identical data. A step
  that does less real work than a true assign+update lands worse centroids after
  two iterations and fails this.

The gate is permutation/convention-independent and cheat-proof. `init_centroids`
are always supplied by the judge, so the baseline is deterministic in
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

## Timing unit — the judge-owned loop

The timed unit is the **judge's loop of `max_iters` `step` calls** (warmup
`warmup_iters`, then `timed_iters = 1` timed run) — baseline and agent time the
identical loop on the same seeded data + init. `max_iters = 2`: a genuine loop
(so a bad step propagates and is caught by the inertia gate) but too few for a
converged step to become a redundant no-op. The score isolates per-`step` kernel
efficiency, since loop count is identical on both sides.

## Calibration (H100 Modal trial — done, step / max_iters=2)

Final setup (bf16 + `step` contract + judge-owned loop of `max_iters=2` + planted
clusters + centroid inertia gate): the flashlib `reference.patch` compiles + runs
on bf16 and **passes the centroid gate on all 6 workloads**, running
**2.1 / 2.4 / 6.7 / 3.5 / 13.2 / 9.3x** over the bf16 naive baseline (geomean
**4.95x**). `speedup_target = 5.0`. The worst reference bf16 inertia drift is
**+1.47%** (w3, D=512), so `inertia_tolerance = 0.05` clears it with margin while
still rejecting genuinely bad centroids. This speedup is a *pure kernel-structure*
win — both sides bf16 (precision is not a lever), and the judge owns the loop (so
iteration-skip / fake-labels / subsample are not levers either).

(Prior `max_iters=1` calibration, for the record: bf16 + planted clusters +
labelled/centroid gates gave the flashlib reference geomean **4.54x**, all 6
passing. That setting let the agent own the whole `kmeans(...)` call, which is why
iteration-skip was still reachable and motivated this `step` restructure. The
geomean is essentially unchanged (4.54 → 4.95) because the reference does the same
per-step work; what changed is that the hack surface is now closed structurally.)
