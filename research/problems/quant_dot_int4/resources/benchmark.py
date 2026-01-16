import math
from typing import Optional, Tuple, List, Callable

import torch
import triton

FPINT = 32 // 4  # 8 int4 per int32
GROUP = 8
K = FPINT * GROUP  # 64

# Ensure CUDA is available and properly initialize device
if not torch.cuda.is_available():
    raise RuntimeError("CUDA is not available. This benchmark requires a CUDA-enabled GPU.")
DEVICE = torch.device("cuda:0")
torch.cuda.set_device(DEVICE)


def alloc_fn(size: int, align: int, stream: Optional[int]):
    assert align == 128
    assert stream == 0
    return torch.empty(size, dtype=torch.int8, device=DEVICE)


triton.set_allocator(alloc_fn)
torch.manual_seed(0)
try:
    torch.cuda.manual_seed_all(0)
except Exception:
    pass
assert triton.runtime.driver.active.get_current_target().backend == "cuda", "This benchmark only supports CUDA backend."


def _bench_ms(fn) -> float:
    out = triton.testing.do_bench(fn, quantiles=[0.5])
    if isinstance(out, (tuple, list)):
        return float(out[0])
    return float(out)


def _is_close(x: torch.Tensor, y: torch.Tensor, rtol=1e-2, atol=5e-3) -> bool:
    return torch.allclose(x, y, rtol=rtol, atol=atol)


def _pack_int4_signed(x: torch.Tensor) -> torch.Tensor:
    """
    Pack last-dim length 8 signed int4 values (-8..7) into int32.
    x: (...,8) int32
    returns (...,) int32
    """
    assert x.shape[-1] == FPINT
    x = x.to(torch.int32)
    # to unsigned nibble 0..15
    u = (x + 16) % 16
    shifts = (torch.arange(FPINT, device=x.device, dtype=torch.int32) * 4)
    return (u << shifts).sum(dim=-1).to(torch.int32)


def _gen_case(M: int, N: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Generate inputs matching Puzzle-12 semantics:
      scale: (M,8) float16
      offset_packed: (M,) int32 (packs 8 int4 offsets)
      weight_packed: (M,8) int32 (packs 8 int4 weights)
      activation: (64,N) float16
    """
    offset_int4 = torch.randint(-8, 8, (M, FPINT), device=DEVICE, dtype=torch.int32)

    # Scale in fp16, keep range modest for numeric stability
    scale = (torch.rand((M, FPINT), device=DEVICE, dtype=torch.float16) * 0.5 + 0.5)

    activation = torch.randn((K, N), device=DEVICE, dtype=torch.float16)

    # weight_packed for kernel expects (M,8) int32, keep the same shape as puzzles
    # In puzzles, weight is Int32[32,8]. Here we keep (M,8) by expanding packs? No:
    # each row has 8 packs already -> represent as (M,8) int32 (one pack per FPINT position)
    # Our pack_int4 packs 8 values into one int32; for puzzle weight it is (M,8) int32.
    # So we need 8 packs -> use a second dimension: generate (M,8,8) int4 then pack -> (M,8).
    weight_int4_full = torch.randint(-8, 8, (M, FPINT, GROUP), device=DEVICE, dtype=torch.int32)
    # Pack each FPINT lane's GROUP=8 values into one int32 => (M, 8)
    weight_packed = _pack_int4_signed(weight_int4_full).to(torch.int32)

    # offset is per row: 8 offsets; pack from offset_int4: (M,)
    offset_packed = _pack_int4_signed(offset_int4)

    # scale is per (M,8)
    return scale, offset_packed, weight_packed, activation


def _warmup_gpu(iters: int = 10):
    try:
        scale, offset_packed, weight_packed, activation = _gen_case(256, 256)
        from quant_dot_baseline import quant_dot as baseline
        for _ in range(max(1, int(iters))):
            _ = baseline(scale, offset_packed, weight_packed, activation)
        torch.cuda.synchronize()
    except Exception:
        pass


def _bench_pair(M: int, N: int, answer_fn: Callable, baseline_fn: Callable):
    scale, offset_packed, weight_packed, activation = _gen_case(M, N)

    baseline_ms = _bench_ms(lambda: baseline_fn(scale, offset_packed, weight_packed, activation))
    answer_ms = _bench_ms(lambda: answer_fn(scale, offset_packed, weight_packed, activation))

    ref = baseline_fn(scale, offset_packed, weight_packed, activation)
    out = answer_fn(scale, offset_packed, weight_packed, activation)
    passed = _is_close(out, ref, rtol=1e-2, atol=5e-3)

    return {
        "M": M, "N": N, "K": K,
        "baseline_ms": baseline_ms,
        "answer_ms": answer_ms,
        "close_passed": passed,
        "rtol": 1e-2, "atol": 5e-3, "passed": passed,
    }


def summarize_speedup(answer_fn, baseline_fn, print_output: bool = False):
    _warmup_gpu(10)

    shapes: List[Tuple[int, int]] = [
        (256, 256),
        (512, 256),
        (512, 512),
        (1024, 256),
        (1024, 512),
        (2048, 256),
    ]

    rows = []
    for (M, N) in shapes:
        rows.append(_bench_pair(M, N, answer_fn, baseline_fn))

    speedups = []
    for r in rows:
        sp = r["baseline_ms"] / r["answer_ms"]
        speedups.append(sp)

    arith_mean = sum(speedups) / len(speedups) if speedups else 0.0
    geo_mean = math.exp(sum(math.log(s) for s in speedups) / len(speedups)) if speedups else 0.0
    median = sorted(speedups)[len(speedups)//2] if speedups else 0.0

    if print_output:
        print("\n=== Answer vs Baseline ===")
        for r, sp in zip(rows, speedups):
            status = "OK" if r["close_passed"] else "FAIL"
            print(
                f"M={r['M']:5d} N={r['N']:5d} K={r['K']:3d}  "
                f"baseline={r['baseline_ms']:7.3f} ms  answer={r['answer_ms']:7.3f} ms  "
                f"speedup={sp:5.2f}x  [Passed: {status}]"
            )
        print(f"\nGeometric mean speedup: {geo_mean:.3f}x")

    return rows, arith_mean, geo_mean, median


def run_benchmark(answer_fn, baseline_fn, print_output: bool = False):
    rows, arith_mean, geo_mean, median = summarize_speedup(answer_fn, baseline_fn, print_output=print_output)
    return {
        "rows": rows,
        "arithmetic_mean_speedup": arith_mean,
        "geometric_mean_speedup": geo_mean,
        "median_speedup": median,
        "pass_all": all(r["close_passed"] for r in rows),
    }


