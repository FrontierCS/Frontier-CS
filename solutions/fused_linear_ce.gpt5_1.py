import torch
import triton
import triton.language as tl


@triton.jit
def _rowmax_kernel(
    X_ptr, W_ptr, B_ptr, rowmax_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    row_max = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)

    for n0 in range(0, N, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k0 in range(0, K, BLOCK_K):
            offs_k = k0 + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

            x = tl.load(x_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)

            acc += tl.dot(x, w)

        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
        acc += b[None, :]

        tile_max = tl.max(acc, axis=1)
        row_max = tl.maximum(row_max, tile_max)

    tl.store(rowmax_ptr + offs_m, row_max, mask=mask_m)


@triton.jit
def _lse_tgt_kernel(
    X_ptr, W_ptr, B_ptr, rowmax_ptr, targets_ptr, out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    rowmax = tl.load(rowmax_ptr + offs_m, mask=mask_m, other=-float("inf"))
    tgt = tl.load(targets_ptr + offs_m, mask=mask_m, other=0).to(tl.int64)

    sumexp = tl.zeros([BLOCK_M], dtype=tl.float32)
    tgt_logit = tl.zeros([BLOCK_M], dtype=tl.float32)

    for n0 in range(0, N, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k0 in range(0, K, BLOCK_K):
            offs_k = k0 + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

            x = tl.load(x_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)

            acc += tl.dot(x, w)

        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
        acc += b[None, :]

        e = tl.exp(acc - rowmax[:, None])
        sumexp += tl.sum(e, axis=1)

        offs_n_i64 = offs_n.to(tl.int64)
        eq = (tgt[:, None] == offs_n_i64[None, :])
        eqf = eq.to(tl.float32)
        tgt_logit += tl.sum(acc * eqf, axis=1)

    loss = (rowmax + tl.log(sumexp)) - tgt_logit
    tl.store(out_ptr + offs_m, loss, mask=mask_m)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be CUDA tensors"
    assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.long, "targets must be int64 (long)"
    assert X.shape[1] == W.shape[0], "Incompatible shapes for matmul"
    assert W.shape[1] == B.shape[0], "Bias dimension must match number of classes"
    assert X.shape[0] == targets.shape[0], "Batch size mismatch"

    M, K = X.shape
    K2, N = W.shape
    assert K == K2

    # Ensure contiguous memory for better performance
    Xc = X.contiguous()
    Wc = W.contiguous()
    Bc = B.contiguous()
    tc = targets.contiguous()

    out = torch.empty((M,), device=X.device, dtype=torch.float32)
    rowmax = torch.empty((M,), device=X.device, dtype=torch.float32)

    # Strides in elements
    stride_xm, stride_xk = Xc.stride()
    stride_wk, stride_wn = Wc.stride()

    # Tuneable meta-parameters
    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 64
    NUM_WARPS = 8
    NUM_STAGES = 4

    grid = (triton.cdiv(M, BLOCK_M),)

    _rowmax_kernel[grid](
        Xc, Wc, Bc, rowmax,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=NUM_WARPS, num_stages=NUM_STAGES
    )

    _lse_tgt_kernel[grid](
        Xc, Wc, Bc, rowmax, tc, out,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=NUM_WARPS, num_stages=NUM_STAGES
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            "@triton.jit\n"
            "def _rowmax_kernel(\n"
            "    X_ptr, W_ptr, B_ptr, rowmax_ptr,\n"
            "    M, N, K,\n"
            "    stride_xm, stride_xk,\n"
            "    stride_wk, stride_wn,\n"
            "    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,\n"
            "):\n"
            "    pid_m = tl.program_id(0)\n"
            "    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n"
            "    mask_m = offs_m < M\n"
            "    row_max = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)\n"
            "    for n0 in range(0, N, BLOCK_N):\n"
            "        offs_n = n0 + tl.arange(0, BLOCK_N)\n"
            "        mask_n = offs_n < N\n"
            "        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)\n"
            "        for k0 in range(0, K, BLOCK_K):\n"
            "            offs_k = k0 + tl.arange(0, BLOCK_K)\n"
            "            mask_k = offs_k < K\n"
            "            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk\n"
            "            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn\n"
            "            x = tl.load(x_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)\n"
            "            w = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)\n"
            "            acc += tl.dot(x, w)\n"
            "        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)\n"
            "        acc += b[None, :]\n"
            "        tile_max = tl.max(acc, axis=1)\n"
            "        row_max = tl.maximum(row_max, tile_max)\n"
            "    tl.store(rowmax_ptr + offs_m, row_max, mask=mask_m)\n\n"
            "@triton.jit\n"
            "def _lse_tgt_kernel(\n"
            "    X_ptr, W_ptr, B_ptr, rowmax_ptr, targets_ptr, out_ptr,\n"
            "    M, N, K,\n"
            "    stride_xm, stride_xk,\n"
            "    stride_wk, stride_wn,\n"
            "    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,\n"
            "):\n"
            "    pid_m = tl.program_id(0)\n"
            "    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n"
            "    mask_m = offs_m < M\n"
            "    rowmax = tl.load(rowmax_ptr + offs_m, mask=mask_m, other=-float('inf'))\n"
            "    tgt = tl.load(targets_ptr + offs_m, mask=mask_m, other=0).to(tl.int64)\n"
            "    sumexp = tl.zeros([BLOCK_M], dtype=tl.float32)\n"
            "    tgt_logit = tl.zeros([BLOCK_M], dtype=tl.float32)\n"
            "    for n0 in range(0, N, BLOCK_N):\n"
            "        offs_n = n0 + tl.arange(0, BLOCK_N)\n"
            "        mask_n = offs_n < N\n"
            "        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)\n"
            "        for k0 in range(0, K, BLOCK_K):\n"
            "            offs_k = k0 + tl.arange(0, BLOCK_K)\n"
            "            mask_k = offs_k < K\n"
            "            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk\n"
            "            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn\n"
            "            x = tl.load(x_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)\n"
            "            w = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)\n"
            "            acc += tl.dot(x, w)\n"
            "        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)\n"
            "        acc += b[None, :]\n"
            "        e = tl.exp(acc - rowmax[:, None])\n"
            "        sumexp += tl.sum(e, axis=1)\n"
            "        offs_n_i64 = offs_n.to(tl.int64)\n"
            "        eq = (tgt[:, None] == offs_n_i64[None, :])\n"
            "        eqf = eq.to(tl.float32)\n"
            "        tgt_logit += tl.sum(acc * eqf, axis=1)\n"
            "    loss = (rowmax + tl.log(sumexp)) - tgt_logit\n"
            "    tl.store(out_ptr + offs_m, loss, mask=mask_m)\n\n"
            "def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:\n"
            "    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, 'All inputs must be CUDA tensors'\n"
            "    assert X.dtype == torch.float16 and W.dtype == torch.float16, 'X and W must be float16'\n"
            "    assert B.dtype == torch.float32, 'B must be float32'\n"
            "    assert targets.dtype == torch.long, 'targets must be int64 (long)'\n"
            "    assert X.shape[1] == W.shape[0], 'Incompatible shapes for matmul'\n"
            "    assert W.shape[1] == B.shape[0], 'Bias dimension must match number of classes'\n"
            "    assert X.shape[0] == targets.shape[0], 'Batch size mismatch'\n"
            "    M, K = X.shape\n"
            "    K2, N = W.shape\n"
            "    assert K == K2\n"
            "    Xc = X.contiguous()\n"
            "    Wc = W.contiguous()\n"
            "    Bc = B.contiguous()\n"
            "    tc = targets.contiguous()\n"
            "    out = torch.empty((M,), device=X.device, dtype=torch.float32)\n"
            "    rowmax = torch.empty((M,), device=X.device, dtype=torch.float32)\n"
            "    stride_xm, stride_xk = Xc.stride()\n"
            "    stride_wk, stride_wn = Wc.stride()\n"
            "    BLOCK_M = 64\n"
            "    BLOCK_N = 128\n"
            "    BLOCK_K = 64\n"
            "    NUM_WARPS = 8\n"
            "    NUM_STAGES = 4\n"
            "    grid = (triton.cdiv(M, BLOCK_M),)\n"
            "    _rowmax_kernel[grid](\n"
            "        Xc, Wc, Bc, rowmax,\n"
            "        M, N, K,\n"
            "        stride_xm, stride_xk,\n"
            "        stride_wk, stride_wn,\n"
            "        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,\n"
            "        num_warps=NUM_WARPS, num_stages=NUM_STAGES\n"
            "    )\n"
            "    _lse_tgt_kernel[grid](\n"
            "        Xc, Wc, Bc, rowmax, tc, out,\n"
            "        M, N, K,\n"
            "        stride_xm, stride_xk,\n"
            "        stride_wk, stride_wn,\n"
            "        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,\n"
            "        num_warps=NUM_WARPS, num_stages=NUM_STAGES\n"
            "    )\n"
            "    return out\n"
        )
        return {"code": code}
