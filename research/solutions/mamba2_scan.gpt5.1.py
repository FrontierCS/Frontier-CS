import os
import sys
import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def _mamba2_chunk_prep(
    X_ptr,
    A_ptr,
    B_ptr,
    prod_ptr,
    yzero_ptr,
    L,
    D,
    stride_x_l,
    stride_x_d,
    stride_a_l,
    stride_a_d,
    stride_b_l,
    stride_b_d,
    stride_p_c,
    stride_p_d,
    stride_yz_c,
    stride_yz_d,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    base_l = pid_chunk * CHUNK

    prod = tl.ones([BD], dtype=tl.float32)
    y = tl.zeros([BD], dtype=tl.float32)

    for i in tl.static_range(0, CHUNK):
        l = base_l + i

        x = tl.load(
            X_ptr + l * stride_x_l + offs_d * stride_x_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        a = tl.load(
            A_ptr + l * stride_a_l + offs_d * stride_a_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        b = tl.load(
            B_ptr + l * stride_b_l + offs_d * stride_b_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)

        y = a * y + b * x
        prod = prod * a

    tl.store(
        prod_ptr + pid_chunk * stride_p_c + offs_d * stride_p_d,
        prod,
        mask=mask_d,
    )
    tl.store(
        yzero_ptr + pid_chunk * stride_yz_c + offs_d * stride_yz_d,
        y,
        mask=mask_d,
    )


@triton.jit
def _mamba2_chunk_scan(
    X_ptr,
    A_ptr,
    B_ptr,
    init_ptr,
    Y_ptr,
    L,
    D,
    stride_x_l,
    stride_x_d,
    stride_a_l,
    stride_a_d,
    stride_b_l,
    stride_b_d,
    stride_init_c,
    stride_init_d,
    stride_y_l,
    stride_y_d,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    base_l = pid_chunk * CHUNK

    s = tl.load(
        init_ptr + pid_chunk * stride_init_c + offs_d * stride_init_d,
        mask=mask_d,
        other=0.0,
    ).to(tl.float32)

    for i in tl.static_range(0, CHUNK):
        l = base_l + i

        x = tl.load(
            X_ptr + l * stride_x_l + offs_d * stride_x_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        a = tl.load(
            A_ptr + l * stride_a_l + offs_d * stride_a_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        b = tl.load(
            B_ptr + l * stride_b_l + offs_d * stride_b_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)

        s = a * s + b * x

        tl.store(
            Y_ptr + l * stride_y_l + offs_d * stride_y_d,
            s.to(tl.float16),
            mask=mask_d,
        )


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.

    y_t = a_t * y_{t-1} + b_t * x_t
    """
    assert X.device.type == "cuda", "X must be on CUDA device"
    assert A.device == X.device and B.device == X.device, "A and B must be on same device as X"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
    assert X.shape == A.shape == B.shape, "X, A, B must have same shape"
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"

    Xc = X.contiguous()
    Ac = A.contiguous()
    Bc = B.contiguous()
    Y = torch.empty_like(Xc)

    num_chunks = L // chunk

    # Preparation kernel: compute per-chunk product of A and end-state with zero initial condition
    prod_a = torch.empty((num_chunks, D), dtype=torch.float32, device=X.device)
    y_zero = torch.empty_like(prod_a)

    grid_prep = (num_chunks, triton.cdiv(D, BD))
    _mamba2_chunk_prep[grid_prep](
        Xc,
        Ac,
        Bc,
        prod_a,
        y_zero,
        L,
        D,
        Xc.stride(0),
        Xc.stride(1),
        Ac.stride(0),
        Ac.stride(1),
        Bc.stride(0),
        Bc.stride(1),
        prod_a.stride(0),
        prod_a.stride(1),
        y_zero.stride(0),
        y_zero.stride(1),
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    # Compute initial state for each chunk on GPU using PyTorch
    init_state = torch.zeros((num_chunks, D), dtype=torch.float32, device=X.device)
    if num_chunks > 1:
        for k in range(1, num_chunks):
            init_state[k] = prod_a[k - 1] * init_state[k - 1] + y_zero[k - 1]

    # Final scan kernel using correct initial state per chunk
    grid_scan = (num_chunks, triton.cdiv(D, BD))
    _mamba2_chunk_scan[grid_scan](
        Xc,
        Ac,
        Bc,
        init_state,
        Y,
        L,
        D,
        Xc.stride(0),
        Xc.stride(1),
        Ac.stride(0),
        Ac.stride(1),
        Bc.stride(0),
        Bc.stride(1),
        init_state.stride(0),
        init_state.stride(1),
        Y.stride(0),
        Y.stride(1),
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            code = open(__file__, "r", encoding="utf-8").read()
        except Exception:
            module = sys.modules[__name__]
            code = inspect.getsource(module)
        return {"code": code}
