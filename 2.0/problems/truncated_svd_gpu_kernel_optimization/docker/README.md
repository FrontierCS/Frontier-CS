# Experimental Truncated-SVD Kernel-Optimization Images

Two **light** images (ubuntu + `modal` + git). torch, triton, and the vendored
flashlib kernels all run on the **Modal GPU image** defined in `flash_gpu.py`;
the containers themselves are CPU-only and offload GPU work to Modal.

```bash
bash 2.0/problems/truncated_svd_gpu_kernel_optimization/docker/build_images.sh
```

Defaults:

```text
AGENT_TAG=frontiercs/truncated-svd-gpu-kernel-optimization-agent:experimental-v0.2.0
JUDGE_TAG=frontiercs/truncated-svd-gpu-kernel-optimization-judge:experimental-v0.2.0
```

Agent image:

```text
/app/tsvdlib             # clean, git-tracked package (the agent edits this)
/opt/flash_gpu.py        # shared Modal GPU harness (public test uses it)
/opt/tsvd_ref/reftsvd.py # frozen naive baseline (public-test speed denominator)
```

Judge image:

```text
/opt/tsvdlib-clean/tsvdlib   # pristine tree; the patch is applied to a copy
/opt/tsvd_ref/reftsvd.py     # frozen naive baseline (speed denominator + quality oracle)
/opt/flash_gpu.py            # shared Modal GPU harness (the evaluator uses it)
```

## Runtime requirements

Both the judge and the agent public test **offload timing to a Modal GPU** and
therefore need Modal credentials in the environment:

```text
MODAL_TOKEN_ID / MODAL_TOKEN_SECRET
```

`flash_gpu.py` builds an ephemeral Modal app on a GPU (`evaluation.gpu`, default
`H100`), ships the frozen baseline + the patched package as data, times both on
fresh per-iteration data, verifies quality each iteration, and returns the
speedups. No persistent deployment is used, so a fresh GPU container is spun up
per evaluation. Without Modal credentials the evaluator returns a patch-policy
smoke pass (which repo CI exercises).

## Smoke test

```bash
bash 2.0/problems/truncated_svd_gpu_kernel_optimization/docker/smoke_images.sh
```

Import-only (modal + flash_gpu + the baked packages); does not touch a GPU or Modal.
