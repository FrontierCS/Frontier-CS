import os
import torch
import triton
import triton.language as tl


@triton.jit
def fused_linear_ce_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    targets_ptr,
    out_ptr,
    M,
    N,
    K,
    stride_xm,
    stride_xk,
    stride_wk,
    stride_wn,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    row_idx = tl.program_id(0)
    if row_idx >= M:
        return

    x_row_ptr = X_ptr + row_idx * stride_xm
    target = tl.load(targets_ptr + row_idx)

    m_curr = tl.full((), -float("inf"), tl.float32)
    s_curr = tl.zeros((), tl.float32)
    target_logit = tl.zeros((), tl.float32)

    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc = tl.zeros((BLOCK_N,), tl.float32)

        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            x = tl.load(
                x_row_ptr + offs_k * stride_xk,
                mask=mask_k,
                other=0.0,
            )
            w = tl.load(
                W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            )

            x_f32 = x.to(tl.float32)
            w_f32 = w.to(tl.float32)
            acc += tl.sum(x_f32[:, None] * w_f32, axis=0)

        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
        logits = acc + b
        logits = tl.where(mask_n, logits, -float("inf"))

        block_max = tl.max(logits, axis=0)
        new_m = tl.maximum(m_curr, block_max)

        s_prev_scaled = s_curr * tl.exp(m_curr - new_m)
        exp_logits = tl.exp(logits - new_m)
        s_block = tl.sum(exp_logits, axis=0)
        s_curr = s_prev_scaled + s_block
        m_curr = new_m

        target_i32 = target.to(tl.int32)
        col_indices = tl.arange(0, BLOCK_N)
        mask_eq = col_indices == (target_i32 - n_start)
        mask_eq = mask_eq & mask_n
        contrib = tl.sum(logits * mask_eq, axis=0)
        target_logit += contrib

    logsumexp = m_curr + tl.log(s_curr)
    nll = logsumexp - target_logit
    tl.store(out_ptr + row_idx, nll)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K
    assert B.shape[0] == N
    assert targets.shape[0] == M

    out = torch.empty(M, device=X.device, dtype=torch.float32)

    BLOCK_N = 128
    BLOCK_K = 32

    grid = (M,)

    fused_linear_ce_kernel[grid](
        X,
        W,
        B,
        targets,
        out,
        M,
        N,
        K,
        X.stride(0),
        X.stride(1),
        W.stride(0),
        W.stride(1),
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            file_path = os.path.abspath(__file__)
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            return {"code": code}
        except Exception:
            # Fallback: directly return minimal working code string
            code = (
                "import torch\n"
                "import triton\n"
                "import triton.language as tl\n\n"
                "@triton.jit\n"
                "def fused_linear_ce_kernel(\n"
                "    X_ptr,\n"
                "    W_ptr,\n"
                "    B_ptr,\n"
                "    targets_ptr,\n"
                "    out_ptr,\n"
                "    M,\n"
                "    N,\n"
                "    K,\n"
                "    stride_xm,\n"
                "    stride_xk,\n"
                "    stride_wk,\n"
                "    stride_wn,\n"
                "    BLOCK_N: tl.constexpr,\n"
                "    BLOCK_K: tl.constexpr,\n"
                "):\n"
                "    row_idx = tl.program_id(0)\n"
                "    if row_idx >= M:\n"
                "        return\n"
                "    x_row_ptr = X_ptr + row_idx * stride_xm\n"
                "    target = tl.load(targets_ptr + row_idx)\n"
                "    m_curr = tl.full((), -float('inf'), tl.float32)\n"
                "    s_curr = tl.zeros((), tl.float32)\n"
                "    target_logit = tl.zeros((), tl.float32)\n"
                "    for n_start in range(0, N, BLOCK_N):\n"
                "        offs_n = n_start + tl.arange(0, BLOCK_N)\n"
                "        mask_n = offs_n < N\n"
                "        acc = tl.zeros((BLOCK_N,), tl.float32)\n"
                "        for k_start in range(0, K, BLOCK_K):\n"
                "            offs_k = k_start + tl.arange(0, BLOCK_K)\n"
                "            mask_k = offs_k < K\n"
                "            x = tl.load(\n"
                "                x_row_ptr + offs_k * stride_xk,\n"
                "                mask=mask_k,\n"
                "                other=0.0,\n"
                "            )\n"
                "            w = tl.load(\n"
                "                W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn,\n"
                "                mask=mask_k[:, None] & mask_n[None, :],\n"
                "                other=0.0,\n"
                "            )\n"
                "            x_f32 = x.to(tl.float32)\n"
                "            w_f32 = w.to(tl.float32)\n"
                "            acc += tl.sum(x_f32[:, None] * w_f32, axis=0)\n"
                "        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)\n"
                "        logits = acc + b\n"
                "        logits = tl.where(mask_n, logits, -float('inf'))\n"
                "        block_max = tl.max(logits, axis=0)\n"
                "        new_m = tl.maximum(m_curr, block_max)\n"
                "        s_prev_scaled = s_curr * tl.exp(m_curr - new_m)\n"
                "        exp_logits = tl.exp(logits - new_m)\n"
                "        s_block = tl.sum(exp_logits, axis=0)\n"
                "        s_curr = s_prev_scaled + s_block\n"
                "        m_curr = new_m\n"
                "        target_i32 = target.to(tl.int32)\n"
                "        col_indices = tl.arange(0, BLOCK_N)\n"
                "        mask_eq = col_indices == (target_i32 - n_start)\n"
                "        mask_eq = mask_eq & mask_n\n"
                "        contrib = tl.sum(logits * mask_eq, axis=0)\n"
                "        target_logit += contrib\n"
                "    logsumexp = m_curr + tl.log(s_curr)\n"
                "    nll = logsumexp - target_logit\n"
                "    tl.store(out_ptr + row_idx, nll)\n\n"
                "def fused_linear_ce(X, W, B, targets):\n"
                "    M, K = X.shape\n"
                "    K_w, N = W.shape\n"
                "    assert K_w == K\n"
                "    assert B.shape[0] == N\n"
                "    assert targets.shape[0] == M\n"
                "    out = torch.empty(M, device=X.device, dtype=torch.float32)\n"
                "    BLOCK_N = 128\n"
                "    BLOCK_K = 32\n"
                "    grid = (M,)\n"
                "    fused_linear_ce_kernel[grid](\n"
                "        X,\n"
                "        W,\n"
                "        B,\n"
                "        targets,\n"
                "        out,\n"
                "        M,\n"
                "        N,\n"
                "        K,\n"
                "        X.stride(0),\n"
                "        X.stride(1),\n"
                "        W.stride(0),\n"
                "        W.stride(1),\n"
                "        BLOCK_N=BLOCK_N,\n"
                "        BLOCK_K=BLOCK_K,\n"
                "        num_warps=4,\n"
                "        num_stages=2,\n"
                "    )\n"
                "    return out\n"
            )
            return {"code": code}