"""Public self-test for the PCA kernel-optimization task.

Runs the (patched) pcalib on the two public shapes, checks the subspace quality
(orthonormality + captured variance) against a local naive recomputation, and
prints a rough speedup. This is a convenience for local iteration only -- the
graded workloads and thresholds are hidden and differ from these shapes.
"""
from __future__ import annotations

import sys
import time

PUBLIC_WORKLOADS = [
    {"N": 200_000, "D": 128, "k": 16, "seed": 1},
    {"N": 500_000, "D": 64, "k": 8, "seed": 2},
]


def naive_pca(x, k):
    import torch
    N = x.shape[0]
    mean = x.mean(dim=0)
    xc = x - mean
    U, S, Vh = torch.linalg.svd(xc, full_matrices=False)
    components = Vh[:k].contiguous()
    explained_variance = (S[:k] ** 2) / (N - 1)
    return components, explained_variance.contiguous()


def ortho_err(comps):
    import torch
    c = comps.to(torch.float32)
    k = c.shape[0]
    return float((c @ c.t() - torch.eye(k, device=c.device)).abs().max())


def captured(x, comps):
    import torch
    c = comps.to(torch.float32)
    mean = x.mean(dim=0)
    N = x.shape[0]
    total = 0.0
    for i in range(0, N, 16384):
        p = (x[i:i + 16384] - mean) @ c.t()
        total += float((p * p).sum())
    return total / (N - 1)


def bench(fn, warmup=2, iters=5):
    import torch
    for _ in range(warmup):
        fn(); torch.cuda.synchronize()
    ts = []
    for _ in range(iters):
        torch.cuda.synchronize(); t0 = time.perf_counter()
        fn(); torch.cuda.synchronize()
        ts.append(time.perf_counter() - t0)
    ts.sort()
    return ts[len(ts) // 2] * 1000.0


def main() -> int:
    try:
        import torch
    except Exception as e:  # pragma: no cover
        print(f"torch import failed: {e}")
        return 1
    if not torch.cuda.is_available():
        print("no CUDA device available; run this in a GPU-enabled container.")
        return 1
    import pcalib

    for w in PUBLIC_WORKLOADS:
        N, D, k, seed = w["N"], w["D"], w["k"], w["seed"]
        g = torch.Generator(device="cuda").manual_seed(seed)
        x = torch.randn(N, D, generator=g, device="cuda", dtype=torch.float32)

        ref_c, _ = naive_pca(x, k)
        out = pcalib.pca(x, k)
        agent_c = out[0]
        rc, ac = captured(x, ref_c), captured(x, agent_c)
        ratio = ac / rc if rc > 0 else 0.0
        oerr = ortho_err(agent_c)

        ref_ms = bench(lambda: naive_pca(x, k))
        agent_ms = bench(lambda: pcalib.pca(x, k))
        ok = "OK" if (ratio >= 0.95 and oerr <= 0.02) else "QUALITY REGRESSION"
        print(f"(N={N}, D={D}, k={k}) captured_ratio={ratio:.4f} ortho_err={oerr:.2e} [{ok}]  "
              f"baseline={ref_ms:.2f}ms  yours={agent_ms:.2f}ms  "
              f"speedup={ref_ms / agent_ms:.2f}x")
        del x
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
