import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def partial_max_kernel(
    X_PTR, W_PTR, B_PTR, partial_PTR,
    STRIDE_XM: tl.int32, STRIDE_XK: tl.int32,
    STRIDE_WK: tl.int32, STRIDE_WN: tl.int32, STRIDE_B: tl.int32,
    M: tl.int32, N: tl.int32, K: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    NUM_BLOCKS: tl.int32
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m_start = pid_m * BLOCK_M
    block_n_start = pid_n * BLOCK_N
    offs_m = block_m_start + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    mask_m = offs_m < M
    mask_n = block_n_start + offs_n < N
    out = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    # Load first block
    x_ptrs = X_PTR + (offs_m[:, None] * STRIDE_XM + offs_k[None, :] * STRIDE_XK)
    mask_x = mask_m[:, None] & (offs_k[None, :] < K)
    x = tl.load(x_ptrs, mask=mask_x, other=0.0)
    w_ptrs = W_PTR + (offs_k[:, None] * STRIDE_WK + (block_n_start + offs_n)[None, :] * STRIDE_WN)
    mask_w = (offs_k[:, None] < K) & mask_n[None, :]
    w = tl.load(w_ptrs, mask=mask_w, other=0.0)
    out += tl.dot(x, w)
    # Loop over k
    for start_k in range(BLOCK_K, K, BLOCK_K):
        x_ptrs = X_PTR + (offs_m[:, None] * STRIDE_XM + (start_k + offs_k)[None, :] * STRIDE_XK)
        mask_x = mask_m[:, None] & ((start_k + offs_k)[None, :] < K)
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w_ptrs = W_PTR + ((start_k + offs_k)[:, None] * STRIDE_WK + (block_n_start + offs_n)[None, :] * STRIDE_WN)
        mask_w = ((start_k + offs_k)[:, None] < K) & mask_n[None, :]
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        out += tl.dot(x, w)
    # Add bias
    b_ptrs = B_PTR + (block_n_start + offs_n) * STRIDE_B
    b = tl.load(b_ptrs, mask=mask_n, other=0.0)
    out += b[None, :]
    # Mask padded
    out = tl.where(mask_n[None, :], out, tl.full((BLOCK_M, BLOCK_N), float("-inf"), dtype=tl.float32))
    # Reduce max
    block_max = tl.max(out, 1)
    # Store
    partial_offsets = (block_m_start + tl.arange(0, BLOCK_M)) * NUM_BLOCKS + pid_n
    mask_store = mask_m
    tl.store(partial_PTR + partial_offsets, block_max, mask=mask_store)

@triton.jit
def partial_sum_kernel(
    X_PTR, W_PTR, B_PTR, partial_PTR, row_max_PTR,
    STRIDE_XM: tl.int32, STRIDE_XK: tl.int32,
    STRIDE_WK: tl.int32, STRIDE_WN: tl.int32, STRIDE_B: tl.int32, STRIDE_RM: tl.int32,
    M: tl.int32, N: tl.int32, K: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    NUM_BLOCKS: tl.int32
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m_start = pid_m * BLOCK_M
    block_n_start = pid_n * BLOCK_N
    offs_m = block_m_start + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    mask_m = offs_m < M
    mask_n = block_n_start + offs_n < N
    out = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    # Load first block
    x_ptrs = X_PTR + (offs_m[:, None] * STRIDE_XM + offs_k[None, :] * STRIDE_XK)
    mask_x = mask_m[:, None] & (offs_k[None, :] < K)
    x = tl.load(x_ptrs, mask=mask_x, other=0.0)
    w_ptrs = W_PTR + (offs_k[:, None] * STRIDE_WK + (block_n_start + offs_n)[None, :] * STRIDE_WN)
    mask_w = (offs_k[:, None] < K) & mask_n[None, :]
    w = tl.load(w_ptrs, mask=mask_w, other=0.0)
    out += tl.dot(x, w)
    # Loop over k
    for start_k in range(BLOCK_K, K, BLOCK_K):
        x_ptrs = X_PTR + (offs_m[:, None] * STRIDE_XM + (start_k + offs_k)[None, :] * STRIDE_XK)
        mask_x = mask_m[:, None] & ((start_k + offs_k)[None, :] < K)
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w_ptrs = W_PTR + ((start_k + offs_k)[:, None] * STRIDE_WK + (block_n_start + offs_n)[None, :] * STRIDE_WN)
        mask_w = ((start_k + offs_k)[:, None] < K) & mask_n[None, :]
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        out += tl.dot(x, w)
    # Add bias
    b_ptrs = B_PTR + (block_n_start + offs_n) * STRIDE_B
    b = tl.load(b_ptrs, mask=mask_n, other=0.0)
    out += b[None, :]
    # Subtract row_max
    row_max_block = tl.load(row_max_PTR + (block_m_start + tl.arange(0, BLOCK_M)) * STRIDE_RM, mask=mask_m, other=0.0)
    out -= row_max_block[:, None]
    # Exp
    exps = tl.exp(out)
    # Mask padded
    exps = tl.where(mask_n[None, :], exps, 0.0)
    # Reduce sum
    block_sum = tl.sum(exps, 1)
    # Store
    partial_offsets = (block_m_start + tl.arange(0, BLOCK_M)) * NUM_BLOCKS + pid_n
    mask_store = mask_m
    tl.store(partial_PTR + partial_offsets, block_sum, mask=mask_store)

@triton.jit
def target_logits_kernel(
    X_PTR, W_PTR, B_PTR, targets_PTR, output_PTR,
    STRIDE_XM: tl.int32, STRIDE_XK: tl.int32,
    STRIDE_WK: tl.int32, STRIDE_WN: tl.int32, STRIDE_B: tl.int32, STRIDE_OUT: tl.int32,
    M: tl.int32, N: tl.int32, K: tl.int32,
    BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    target_n = tl.load(targets_PTR + pid * 1)  # assume stride 1
    acc = tl.float32(0.0)
    for k_start in range(0, K, BLOCK_K):
        offs_k = tl.arange(0, BLOCK_K)
        mask_k = k_start + offs_k < K
        x_ptrs = X_PTR + pid * STRIDE_XM + (k_start + offs_k) * STRIDE_XK
        x = tl.load(x_ptrs, mask=mask_k, other=0.0)
        w_ptrs = W_PTR + (k_start + offs_k) * STRIDE_WK + target_n * STRIDE_WN
        w = tl.load(w_ptrs, mask=mask_k, other=0.0)
        acc += tl.sum(x.to(tl.float32) * w.to(tl.float32))
    b = tl.load(B_PTR + target_n * STRIDE_B)
    acc += b
    tl.store(output_PTR + pid * STRIDE_OUT, acc)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert X.is_contiguous()
    assert W.is_contiguous()
    assert B.is_contiguous()
    assert targets.is_contiguous()
    device = X.device
    M, K = X.shape
    Kw, N = W.shape
    assert Kw == K
    assert B.shape[0] == N
    assert targets.shape[0] == M
    BLOCK_M: int = 32
    BLOCK_N: int = 128
    BLOCK_K: int = 64
    TARGET_BLOCK_K: int = 128
    num_blocks = (N + BLOCK_N - 1) // BLOCK_N
    partial_max = torch.zeros((M, num_blocks), dtype=torch.float32, device=device)
    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_wk = W.stride(0)
    stride_wn = W.stride(1)
    stride_b = B.stride(0)
    grid_m = (M + BLOCK_M - 1) // BLOCK_M
    grid = (grid_m, num_blocks)
    partial_max_kernel[grid](
        X, W, B, partial_max,
        torch.int32(stride_xm), torch.int32(stride_xk),
        torch.int32(stride_wk), torch.int32(stride_wn), torch.int32(stride_b),
        torch.int32(M), torch.int32(N), torch.int32(K),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        NUM_BLOCKS=torch.int32(num_blocks)
    )
    row_max = torch.max(partial_max, dim=1)[0]
    partial_sums = torch.zeros((M, num_blocks), dtype=torch.float32, device=device)
    stride_rm = 1
    partial_sum_kernel[grid](
        X, W, B, partial_sums, row_max,
        torch.int32(stride_xm), torch.int32(stride_xk),
        torch.int32(stride_wk), torch.int32(stride_wn), torch.int32(stride_b), torch.int32(stride_rm),
        torch.int32(M), torch.int32(N), torch.int32(K),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        NUM_BLOCKS=torch.int32(num_blocks)
    )
    sum_exp = torch.sum(partial_sums, dim=1)
    target_logits = torch.zeros((M,), dtype=torch.float32, device=device)
    stride_out = 1
    target_logits_kernel[(M,)](
        X, W, B, targets, target_logits,
        torch.int32(stride_xm), torch.int32(stride_xk),
        torch.int32(stride_wk), torch.int32(stride_wn), torch.int32(stride_b), torch.int32(stride_out),
        torch.int32(M), torch.int32(N), torch.int32(K),
        BLOCK_K=TARGET_BLOCK_K
    )
    log_sum_exp = torch.log(sum_exp.clamp(min=1e-8))
    loss = -(target_logits - row_max - log_sum_exp)
    return loss
'''
        return {"code": code}