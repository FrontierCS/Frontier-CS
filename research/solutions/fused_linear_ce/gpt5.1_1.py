import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Loss_ptr,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_t,
    stride_l,
    M,
    N: tl.constexpr, K: tl.constexpr,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    # Pointers for this row
    x_row_ptr = X_ptr + pid_m * stride_xm

    # Load target index for this row
    t = tl.load(T_ptr + pid_m * stride_t)
    t_i32 = t.to(tl.int32)

    # Streaming log-sum-exp state
    m = tl.full((), -float("inf"), dtype=tl.float32)
    s = tl.zeros((), dtype=tl.float32)
    target_logit = tl.zeros((), dtype=tl.float32)

    # Loop over blocks of columns N
    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Accumulator for logits block
        acc = tl.zeros((BLOCK_N,), dtype=tl.float32)

        # Loop over K dimension
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            # Load X row fragment
            x_ptrs = x_row_ptr + offs_k * stride_xk
            x = tl.load(x_ptrs, mask=mask_k, other=0.0).to(tl.float32)

            # Load W tile [BLOCK_K, BLOCK_N]
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
            w = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float32)

            # Fused dot product
            acc += tl.dot(x, w)

        # Add bias
        b_ptrs = B_ptr + offs_n * stride_b
        b = tl.load(b_ptrs, mask=mask_n, other=0.0)
        logits_block = acc + b

        # Update streaming log-sum-exp over this block
        logits_block_masked = tl.where(mask_n, logits_block, -float("inf"))
        block_max = tl.max(logits_block_masked, axis=0)
        new_m = tl.maximum(m, block_max)

        exp_scale = tl.exp(m - new_m)
        exp_block = tl.exp(logits_block - new_m)
        exp_block = tl.where(mask_n, exp_block, 0.0)
        block_sumexp = tl.sum(exp_block, axis=0)

        s = s * exp_scale + block_sumexp
        m = new_m

        # Accumulate target logit
        mask_target = mask_n & (offs_n == t_i32)
        target_logit += tl.sum(tl.where(mask_target, logits_block, 0.0), axis=0)

    loss = tl.log(s) + m - target_logit
    tl.store(Loss_ptr + pid_m * stride_l, loss)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.

    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
        targets: Target tensor of shape (M,) - target class indices (int64)

    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss per sample (float32)
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All tensors must be on CUDA device"

    # Ensure dtypes
    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.long, "targets must be int64 (long)"

    # Shapes
    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible shapes between X and W"
    assert B.shape[0] == N, "Bias shape mismatch"
    assert targets.shape[0] == M, "Targets shape mismatch"

    # Make tensors contiguous if needed (common case is already contiguous)
    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()
    if not targets.is_contiguous():
        targets = targets.contiguous()

    # Output tensor
    loss = torch.empty((M,), device=X.device, dtype=torch.float32)

    # Strides in elements
    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_b = B.stride(0)
    stride_t = targets.stride(0)
    stride_l = loss.stride(0)

    # Kernel launch parameters
    BLOCK_N = 128
    BLOCK_K = 32
    num_warps = 4
    num_stages = 3

    grid = (M,)

    fused_linear_ce_kernel[grid](
        X, W, B, targets, loss,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_t,
        stride_l,
        M,
        N, K,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    return loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code_parts = [
            "import torch",
            "import triton",
            "import triton.language as tl",
            "",
            inspect.getsource(fused_linear_ce_kernel),
            "",
            inspect.getsource(fused_linear_ce),
        ]
        code = "\n".join(code_parts)
        return {"code": code}