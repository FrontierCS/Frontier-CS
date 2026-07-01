"""Public self-test for the K-Means kernel-optimization task.

Runs the (patched) kmeanslib on the two public shapes, checks the clustering
quality against a local naive recomputation, and prints a rough speedup. This is
a convenience for local iteration only -- the graded workloads and thresholds
are hidden and differ from these shapes.
"""
from __future__ import annotations

import sys
import time

PUBLIC_WORKLOADS = [
    {"N": 50_000, "D": 32, "K": 64, "max_iters": 10, "seed": 1},
    {"N": 200_000, "D": 128, "K": 256, "max_iters": 10, "seed": 2},
]


def naive_kmeans(x, k, max_iters, init):
    import torch
    c = init.clone()
    labels = None
    for _ in range(max_iters):
        labels = torch.argmin(torch.cdist(x, c), dim=1)
        sums = torch.zeros((k, x.shape[1]), device=x.device, dtype=torch.float32)
        cnt = torch.zeros((k,), device=x.device, dtype=torch.float32)
        sums.index_add_(0, labels, x.float())
        cnt.index_add_(0, labels, torch.ones(x.shape[0], device=x.device))
        empty = cnt == 0
        cnt = cnt.clamp_min(1.0)
        newc = sums / cnt[:, None]
        if empty.any():
            newc[empty] = c[empty].float()
        c = newc.to(x.dtype)
    return labels, c


def inertia(x, c):
    import torch
    cn = (c * c).sum(1)
    total = 0.0
    for i in range(0, x.shape[0], 16384):
        xb = x[i:i + 16384]
        d = (xb * xb).sum(1, keepdim=True) - 2.0 * xb @ c.t() + cn[None, :]
        total += float(d.min(1).values.clamp_min(0).sum())
    return total


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
    import kmeanslib

    for w in PUBLIC_WORKLOADS:
        N, D, K, it, seed = w["N"], w["D"], w["K"], w["max_iters"], w["seed"]
        g = torch.Generator(device="cuda").manual_seed(seed)
        x = torch.randn(N, D, generator=g, device="cuda", dtype=torch.float32)
        init = x.index_select(0, torch.randperm(N, generator=g, device="cuda")[:K]).clone()

        _, ref_c = naive_kmeans(x, K, it, init)
        out = kmeanslib.kmeans(x, K, max_iters=it, init_centroids=init, tol=0.0)
        agent_c = out[1]
        ri, ai = inertia(x, ref_c), inertia(x, agent_c)
        ratio = ai / ri if ri > 0 else float("inf")

        ref_ms = bench(lambda: naive_kmeans(x, K, it, init))
        agent_ms = bench(lambda: kmeanslib.kmeans(x, K, max_iters=it, init_centroids=init, tol=0.0))
        ok = "OK" if ratio <= 1.05 else "QUALITY REGRESSION"
        print(f"(N={N}, D={D}, K={K}) inertia_ratio={ratio:.4f} [{ok}]  "
              f"baseline={ref_ms:.2f}ms  yours={agent_ms:.2f}ms  "
              f"speedup={ref_ms / agent_ms:.2f}x")
        del x, init
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
