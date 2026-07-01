# Experimental K-Means Kernel-Optimization Images

Two images, mirroring the duckdb-e2e split: a public **agent** image and a
private **judge** image. Build them before a local Harbor trial:

```bash
bash 2.0/problems/kmeans_gpu_kernel_optimization/docker/build_images.sh
```

Defaults:

```text
AGENT_TAG=frontiercs/kmeans-gpu-kernel-optimization-agent:experimental-v0.1.0
JUDGE_TAG=frontiercs/kmeans-gpu-kernel-optimization-judge:experimental-v0.1.0
```

The agent image contains:

```text
/app/kmeanslib            # clean, git-tracked package (the agent edits this)
```

The judge image contains:

```text
/opt/kmeanslib-clean/kmeanslib   # pristine tree; the patch is applied to a copy
/opt/kmeans_ref/refkmeans.py     # frozen naive baseline (speed denominator + oracle)
```

Both are based on `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel` (torch + triton).

## Runtime requirements

The judge times the patched kmeans on a **GPU visible to the judge container**
(single device; H100 reference, Triton paths also run on L40S/A100). If the
Harbor runtime cannot attach a GPU to the judge container, port the worker step
(`_run_worker` in `evaluator.py`) to a Modal GPU offload — see `DESIGN.md`.

## Smoke test

```bash
bash 2.0/problems/kmeans_gpu_kernel_optimization/docker/smoke_images.sh
```

Import-only; verifies torch/triton and the baked packages are importable. It
does not exercise a GPU.
