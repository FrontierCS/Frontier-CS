"""Public self-test for the brute-force k-NN kernel-optimization task.

Runs the (patched) knnlib on the two public shapes, checks the nearest-neighbour
quality (recall@k) against a local naive cdist+topk recomputation, and prints a
rough speedup. This is a convenience for local iteration only -- the graded
workloads and thresholds are hidden and differ from these shapes.
"""
from __future__ import annotations

import sys
import time

PUBLIC_WORKLOADS = [
    {"Q": 1024, "M": 100_000, "D": 64, "k": 10, "seed": 1},
    {"Q": 2048, "M": 200_000, "D": 128, "k": 10, "seed": 2},
]


def naive_knn(queries, database, k):
    import torch
    d2 = torch.cdist(queries, database) ** 2
    dist, idx = torch.topk(d2, k, dim=1, largest=False)
    return dist, idx.to(torch.long)


def recall(agent_idx, ref_idx):
    # Fraction of the true k nearest indices recovered, averaged over queries.
    hit = (agent_idx.unsqueeze(2) == ref_idx.unsqueeze(1)).any(dim=2)
    Q, k = ref_idx.shape
    return float(hit.sum().item()) / (Q * k)


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
    import knnlib

    for w in PUBLIC_WORKLOADS:
        Q, M, D, k, seed = w["Q"], w["M"], w["D"], w["k"], w["seed"]
        g = torch.Generator(device="cuda").manual_seed(seed)
        db = torch.randn(M, D, generator=g, device="cuda", dtype=torch.float32)
        queries = torch.randn(Q, D, generator=g, device="cuda", dtype=torch.float32)

        _, ref_idx = naive_knn(queries, db, k)
        out = knnlib.knn(queries, db, k)
        agent_idx = out[1].long()
        rec = recall(agent_idx, ref_idx)

        ref_ms = bench(lambda: naive_knn(queries, db, k))
        agent_ms = bench(lambda: knnlib.knn(queries, db, k))
        ok = "OK" if rec >= 0.99 else "RECALL REGRESSION"
        print(f"(Q={Q}, M={M}, D={D}, k={k}) recall@k={rec:.4f} [{ok}]  "
              f"baseline={ref_ms:.2f}ms  yours={agent_ms:.2f}ms  "
              f"speedup={ref_ms / agent_ms:.2f}x")
        del queries, db
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
