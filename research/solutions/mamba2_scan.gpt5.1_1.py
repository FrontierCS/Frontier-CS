import torch
import triton
import triton.language as tl


@triton.jit
def mamba2_chunk_build_states_kernel(
    X_ptr, A_ptr, B_ptr,
    P_final_ptr, W_final_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_p_l, stride_p_d,
    stride_w_l, stride_w_d,
    CHUNK: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_d = tl.program_id(0)
    pid_k = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    y_prev = tl.zeros([BLOCK_D], dtype=tl.float32)
    p_prev = tl.ones([BLOCK_D], dtype=tl.float32)

    chunk_start = pid_k * CHUNK

    for i in range(0, CHUNK):
        t = chunk_start + i

        x = tl.load(
            X_ptr + t * stride_x_l + offs_d * stride_x_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        a = tl.load(
            A_ptr + t * stride_a_l + offs_d * stride_a_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        b = tl.load(
            B_ptr + t * stride_b_l + offs_d * stride_b_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)

        y_prev = a * y_prev + b * x
        p_prev = a * p_prev

    tl.store(
        P_final_ptr + pid_k * stride_p_l + offs_d * stride_p_d,
        p_prev,
        mask=mask_d,
    )
    tl.store(
        W_final_ptr + pid_k * stride_w_l + offs_d * stride_w_d,
        y_prev,
        mask=mask_d,
    )


@triton.jit
def mamba2_chunk_prefix_states_kernel(
    P_final_ptr, W_final_ptr, StartStates_ptr,
    D,
    stride_p_l, stride_p_d,
    stride_w_l, stride_w_d,
    stride_s_l, stride_s_d,
    NUM_CHUNKS: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    y_prev = tl.zeros([BLOCK_D], dtype=tl.float32)

    for k in range(0, NUM_CHUNKS):
        tl.store(
            StartStates_ptr + k * stride_s_l + offs_d * stride_s_d,
            y_prev,
            mask=mask_d,
        )
        P = tl.load(
            P_final_ptr + k * stride_p_l + offs_d * stride_p_d,
            mask=mask_d,
            other=1.0,
        ).to(tl.float32)
        W = tl.load(
            W_final_ptr + k * stride_w_l + offs_d * stride_w_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        y_prev = P * y_prev + W


@triton.jit
def mamba2_chunk_apply_states_kernel(
    X_ptr, A_ptr, B_ptr,
    StartStates_ptr, Y_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_s_l, stride_s_d,
    stride_y_l, stride_y_d,
    CHUNK: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_d = tl.program_id(0)
    pid_k = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    y_prev = tl.load(
        StartStates_ptr + pid_k * stride_s_l + offs_d * stride_s_d,
        mask=mask_d,
        other=0.0,
    ).to(tl.float32)

    chunk_start = pid_k * CHUNK

    for i in range(0, CHUNK):
        t = chunk_start + i

        x = tl.load(
            X_ptr + t * stride_x_l + offs_d * stride_x_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        a = tl.load(
            A_ptr + t * stride_a_l + offs_d * stride_a_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)
        b = tl.load(
            B_ptr + t * stride_b_l + offs_d * stride_b_d,
            mask=mask_d,
            other=0.0,
        ).to(tl.float32)

        y = a * y_prev + b * x
        tl.store(
            Y_ptr + t * stride_y_l + offs_d * stride_y_d,
            y.to(tl.float16),
            mask=mask_d,
        )
        y_prev = y


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    assert X.device.type == "cuda", "X must be on CUDA device"
    assert A.device == X.device and B.device == X.device, "All tensors must be on same device"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "All tensors must be float16"
    assert X.shape == A.shape == B.shape, "X, A, B must have same shape"
    assert X.dim() == 2, "X must be 2D (L, D)"

    L, D = X.shape
    assert chunk > 0, "chunk must be positive"
    assert L % chunk == 0, "L must be divisible by chunk"

    num_chunks = L // chunk

    BLOCK_D = min(BD, D)
    if BLOCK_D <= 0:
        BLOCK_D = 1

    device = X.device

    P_final = torch.empty((num_chunks, D), dtype=torch.float32, device=device)
    W_final = torch.empty((num_chunks, D), dtype=torch.float32, device=device)

    grid_build = (triton.cdiv(D, BLOCK_D), num_chunks)

    mamba2_chunk_build_states_kernel[grid_build](
        X, A, B,
        P_final, W_final,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        P_final.stride(0), P_final.stride(1),
        W_final.stride(0), W_final.stride(1),
        CHUNK=chunk,
        BLOCK_D=BLOCK_D,
        num_warps=4,
        num_stages=2,
    )

    start_states = torch.empty((num_chunks, D), dtype=torch.float32, device=device)

    grid_prefix = (triton.cdiv(D, BLOCK_D),)

    mamba2_chunk_prefix_states_kernel[grid_prefix](
        P_final, W_final, start_states,
        D,
        P_final.stride(0), P_final.stride(1),
        W_final.stride(0), W_final.stride(1),
        start_states.stride(0), start_states.stride(1),
        NUM_CHUNKS=num_chunks,
        BLOCK_D=BLOCK_D,
        num_warps=4,
        num_stages=2,
    )

    Y = torch.empty_like(X, dtype=torch.float16)

    grid_apply = (triton.cdiv(D, BLOCK_D), num_chunks)

    mamba2_chunk_apply_states_kernel[grid_apply](
        X, A, B,
        start_states, Y,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        start_states.stride(0), start_states.stride(1),
        Y.stride(0), Y.stride(1),
        CHUNK=chunk,
        BLOCK_D=BLOCK_D,
        num_warps=4,
        num_stages=2,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
