"""Public self-test for the truncated-SVD kernel-optimization task.

Runs the (patched) tsvdlib on the two public shapes, checks the factor quality
against a local naive full-SVD recomputation (orthonormality of the returned
components and the captured-energy ratio), and prints a rough speedup. This is a
convenience for local iteration only -- the graded workloads and thresholds are
hidden and differ from these shapes.
"""
from __future__ import annotations

import sys
import time

PUBLIC_WORKLOADS = [
    {"N": 200_000, "D": 128, "k": 16, "seed": 1},
    {"N": 500_000, "D": 64, "k": 8, "seed": 2},
]


def naive_truncated_svd(x, k):
    import torch
    U, S, Vh = torch.linalg.svd(x, full_matrices=False)
    return S[:k].contiguous(), Vh[:k].contiguous()


def ortho_err(comps):
    import torch
    c = comps.to(torch.float32)
    k = c.shape[0]
    return float((c @ c.t() - torch.eye(k, device=c.device)).abs().max().item())


def captured(x, comps):
    import torch
    c = comps.to(torch.float32)
    total = 0.0
    for i in range(0, x.shape[0], 16384):
        p = x[i:i + 16384] @ c.t()
        total += float((p * p).sum().item())
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
    import tsvdlib

    for w in PUBLIC_WORKLOADS:
        N, D, k, seed = w["N"], w["D"], w["k"], w["seed"]
        g = torch.Generator(device="cuda").manual_seed(seed)
        x = torch.randn(N, D, generator=g, device="cuda", dtype=torch.float32)

        _, ref_c = naive_truncated_svd(x, k)
        out = tsvdlib.truncated_svd(x, k)
        agent_c = out[1]
        rc, ac = captured(x, ref_c), captured(x, agent_c)
        ratio = ac / rc if rc > 0 else float("inf")
        oerr = ortho_err(agent_c)

        ref_ms = bench(lambda: naive_truncated_svd(x, k))
        agent_ms = bench(lambda: tsvdlib.truncated_svd(x, k))
        ok = "OK" if (ratio >= 0.98 and oerr <= 0.02) else "QUALITY REGRESSION"
        print(f"(N={N}, D={D}, k={k}) captured_ratio={ratio:.4f} ortho_err={oerr:.2e} [{ok}]  "
              f"baseline={ref_ms:.2f}ms  yours={agent_ms:.2f}ms  "
              f"speedup={ref_ms / agent_ms:.2f}x")
        del x
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
