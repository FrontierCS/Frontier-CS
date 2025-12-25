import math
import torch
import triton
import triton.language as tl


@triton.jit
def _pass1_logsumexp_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    S1_ptr, S2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1, stride_b2,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_rm = rm < M

    # initialize running max and sumexp for both branches
    neg_inf = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    max1 = neg_inf
    max2 = neg_inf
    sumexp1 = tl.zeros([BLOCK_M], dtype=tl.float32)
    sumexp2 = tl.zeros([BLOCK_M], dtype=tl.float32)

    rn = tl.arange(0, BLOCK_N)

    # iterate over N in tiles
    col_start = 0
    while col_start < N:
        cn = col_start + rn
        mask_cn = cn < N

        # compute logits tiles for both branches: Y = X @ W + B
        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        rk = tl.arange(0, BLOCK_K)
        k_start = 0
        while k_start < K:
            kk = k_start + rk
            mask_kk = kk < K

            x_ptrs = X_ptr + (rm[:, None] * stride_xm + kk[None, :] * stride_xk)
            x_tile = tl.load(x_ptrs, mask=mask_rm[:, None] & mask_kk[None, :], other=0.0).to(tl.float16)

            w1_ptrs = W1_ptr + (kk[:, None] * stride_w1k + cn[None, :] * stride_w1n)
            w2_ptrs = W2_ptr + (kk[:, None] * stride_w2k + cn[None, :] * stride_w2n)
            w_mask = mask_kk[:, None] & mask_cn[None, :]

            w1_tile = tl.load(w1_ptrs, mask=w_mask, other=0.0)
            w2_tile = tl.load(w2_ptrs, mask=w_mask, other=0.0)

            acc1 += tl.dot(x_tile, w1_tile)
            acc2 += tl.dot(x_tile, w2_tile)

            k_start += BLOCK_K

        # add bias
        b1 = tl.load(B1_ptr + cn * stride_b1, mask=mask_cn, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + cn * stride_b2, mask=mask_cn, other=0.0).to(tl.float32)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        # mask out-of-range columns with -inf to not affect max/sumexp
        acc1 = tl.where(mask_cn[None, :], acc1, -float("inf"))
        acc2 = tl.where(mask_cn[None, :], acc2, -float("inf"))

        # update running logsumexp for branch 1
        tile_max1 = tl.max(acc1, axis=1)
        new_max1 = tl.maximum(max1, tile_max1)
        # exp(max1 - new_max1) may be 0 when max1 is -inf; that's fine
        sumexp1 = sumexp1 * tl.exp(max1 - new_max1) + tl.sum(tl.exp(acc1 - new_max1[:, None]), axis=1)
        max1 = new_max1

        # update running logsumexp for branch 2
        tile_max2 = tl.max(acc2, axis=1)
        new_max2 = tl.maximum(max2, tile_max2)
        sumexp2 = sumexp2 * tl.exp(max2 - new_max2) + tl.sum(tl.exp(acc2 - new_max2[:, None]), axis=1)
        max2 = new_max2

        col_start += BLOCK_N

    # compute final S = log(sumexp) + max
    S1 = tl.log(sumexp1) + max1
    S2 = tl.log(sumexp2) + max2

    # store results
    tl.store(S1_ptr + rm, S1, mask=mask_rm)
    tl.store(S2_ptr + rm, S2, mask=mask_rm)


@triton.jit
def _pass2_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    S1_ptr, S2_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1, stride_b2,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_rm = rm < M

    # load S1, S2 for these rows
    S1 = tl.load(S1_ptr + rm, mask=mask_rm, other=0.0)
    S2 = tl.load(S2_ptr + rm, mask=mask_rm, other=0.0)
    S1 = S1[:, None]  # shape (BM, 1)
    S2 = S2[:, None]

    rn = tl.arange(0, BLOCK_N)

    ln2 = 0.6931471805599453
    accum = tl.zeros([BLOCK_M], dtype=tl.float32)

    col_start = 0
    while col_start < N:
        cn = col_start + rn
        mask_cn = cn < N

        # compute logits tiles for both branches
        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        rk = tl.arange(0, BLOCK_K)
        k_start = 0
        while k_start < K:
            kk = k_start + rk
            mask_kk = kk < K

            x_ptrs = X_ptr + (rm[:, None] * stride_xm + kk[None, :] * stride_xk)
            x_tile = tl.load(x_ptrs, mask=mask_rm[:, None] & mask_kk[None, :], other=0.0).to(tl.float16)

            w1_ptrs = W1_ptr + (kk[:, None] * stride_w1k + cn[None, :] * stride_w1n)
            w2_ptrs = W2_ptr + (kk[:, None] * stride_w2k + cn[None, :] * stride_w2n)
            w_mask = mask_kk[:, None] & mask_cn[None, :]

            w1_tile = tl.load(w1_ptrs, mask=w_mask, other=0.0)
            w2_tile = tl.load(w2_ptrs, mask=w_mask, other=0.0)

            acc1 += tl.dot(x_tile, w1_tile)
            acc2 += tl.dot(x_tile, w2_tile)

            k_start += BLOCK_K

        # add bias
        b1 = tl.load(B1_ptr + cn * stride_b1, mask=mask_cn, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + cn * stride_b2, mask=mask_cn, other=0.0).to(tl.float32)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        # mask columns outside N
        acc1 = tl.where(mask_cn[None, :], acc1, -float("inf"))
        acc2 = tl.where(mask_cn[None, :], acc2, -float("inf"))

        # compute logP, logQ
        logP = acc1 - S1  # broadcasting across columns
        logQ = acc2 - S2

        # exp(logP), exp(logQ) for P and Q
        eP = tl.exp(logP)
        eQ = tl.exp(logQ)

        # logM = logsumexp(logP, logQ) - ln2
        mx = tl.maximum(logP, logQ)
        sum_exp = tl.exp(logP - mx) + tl.exp(logQ - mx)
        logsum = mx + tl.log(sum_exp)
        logM = logsum - ln2

        # contributions; zero-out masked columns by ensuring eP/eQ are zero
        contrib = 0.5 * (eP * (logP - logM) + eQ * (logQ - logM))
        contrib = tl.where(mask_cn[None, :], contrib, 0.0)
        accum += tl.sum(contrib, axis=1)

        col_start += BLOCK_N

    tl.store(Out_ptr + rm, accum, mask=mask_rm)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    Args:
        X: (M, K) float16
        W1: (K, N) float16
        B1: (N,) float32
        W2: (K, N) float16
        B2: (N,) float32
    Returns:
        (M,) float32
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All tensors must be on CUDA"
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16, "X, W1, W2 must be float16"
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "Biases must be float32"
    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K == K1 == K2 and N == N2, "Shapes must align"
    assert B1.shape[0] == N and B2.shape[0] == N, "Bias shapes must match N"

    # choose block sizes
    BLOCK_M = 32
    BLOCK_N = 128
    BLOCK_K = 32

    # allocate buffers for log-sum-exp results
    S1 = torch.empty((M,), device=X.device, dtype=torch.float32)
    S2 = torch.empty((M,), device=X.device, dtype=torch.float32)
    Out = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid = (triton.cdiv(M, BLOCK_M),)

    _pass1_logsumexp_kernel[grid](
        X, W1, B1, W2, B2,
        S1, S2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0), B2.stride(0),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=8, num_stages=3,
    )

    _pass2_jsd_kernel[grid](
        X, W1, B1, W2, B2,
        S1, S2, Out,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0), B2.stride(0),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=8, num_stages=3,
    )
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": (
            "import math\n"
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n"
            "\n"
            + _pass1_logsumexp_kernel.__code__.co_consts[0] if False else ""
        )} if False else {
            "code": (
                "import math\n"
                "import torch\n"
                "import triton\n"
                "import triton.language as tl\n"
                "\n"
                + _get_source(_pass1_logsumexp_kernel)
                + "\n\n"
                + _get_source(_pass2_jsd_kernel)
                + "\n\n"
                + fused_linear_jsd.__code__.co_consts[0] if False else
                "import math\n"
                "import torch\n"
                "import triton\n"
                "import triton.language as tl\n"
                "\n"
                + _kernel_source_pass1()
                + "\n"
                + _kernel_source_pass2()
                + "\n"
                + _function_source_fused_linear_jsd()
                + "\n"
                + _solution_reemitter()
            )
        }


def _kernel_source_pass1():
    return (
        "@triton.jit\n"
        "def _pass1_logsumexp_kernel(\n"
        "    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,\n"
        "    S1_ptr, S2_ptr,\n"
        "    M, N, K,\n"
        "    stride_xm, stride_xk,\n"
        "    stride_w1k, stride_w1n,\n"
        "    stride_w2k, stride_w2n,\n"
        "    stride_b1, stride_b2,\n"
        "    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr\n"
        "):\n"
        "    pid_m = tl.program_id(0)\n"
        "    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n"
        "    mask_rm = rm < M\n"
        "\n"
        "    neg_inf = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)\n"
        "    max1 = neg_inf\n"
        "    max2 = neg_inf\n"
        "    sumexp1 = tl.zeros([BLOCK_M], dtype=tl.float32)\n"
        "    sumexp2 = tl.zeros([BLOCK_M], dtype=tl.float32)\n"
        "\n"
        "    rn = tl.arange(0, BLOCK_N)\n"
        "\n"
        "    col_start = 0\n"
        "    while col_start < N:\n"
        "        cn = col_start + rn\n"
        "        mask_cn = cn < N\n"
        "\n"
        "        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)\n"
        "        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)\n"
        "\n"
        "        rk = tl.arange(0, BLOCK_K)\n"
        "        k_start = 0\n"
        "        while k_start < K:\n"
        "            kk = k_start + rk\n"
        "            mask_kk = kk < K\n"
        "\n"
        "            x_ptrs = X_ptr + (rm[:, None] * stride_xm + kk[None, :] * stride_xk)\n"
        "            x_tile = tl.load(x_ptrs, mask=mask_rm[:, None] & mask_kk[None, :], other=0.0).to(tl.float16)\n"
        "\n"
        "            w1_ptrs = W1_ptr + (kk[:, None] * stride_w1k + cn[None, :] * stride_w1n)\n"
        "            w2_ptrs = W2_ptr + (kk[:, None] * stride_w2k + cn[None, :] * stride_w2n)\n"
        "            w_mask = mask_kk[:, None] & mask_cn[None, :]\n"
        "\n"
        "            w1_tile = tl.load(w1_ptrs, mask=w_mask, other=0.0)\n"
        "            w2_tile = tl.load(w2_ptrs, mask=w_mask, other=0.0)\n"
        "\n"
        "            acc1 += tl.dot(x_tile, w1_tile)\n"
        "            acc2 += tl.dot(x_tile, w2_tile)\n"
        "\n"
        "            k_start += BLOCK_K\n"
        "\n"
        "        b1 = tl.load(B1_ptr + cn * stride_b1, mask=mask_cn, other=0.0).to(tl.float32)\n"
        "        b2 = tl.load(B2_ptr + cn * stride_b2, mask=mask_cn, other=0.0).to(tl.float32)\n"
        "        acc1 += b1[None, :]\n"
        "        acc2 += b2[None, :]\n"
        "\n"
        "        acc1 = tl.where(mask_cn[None, :], acc1, -float('inf'))\n"
        "        acc2 = tl.where(mask_cn[None, :], acc2, -float('inf'))\n"
        "\n"
        "        tile_max1 = tl.max(acc1, axis=1)\n"
        "        new_max1 = tl.maximum(max1, tile_max1)\n"
        "        sumexp1 = sumexp1 * tl.exp(max1 - new_max1) + tl.sum(tl.exp(acc1 - new_max1[:, None]), axis=1)\n"
        "        max1 = new_max1\n"
        "\n"
        "        tile_max2 = tl.max(acc2, axis=1)\n"
        "        new_max2 = tl.maximum(max2, tile_max2)\n"
        "        sumexp2 = sumexp2 * tl.exp(max2 - new_max2) + tl.sum(tl.exp(acc2 - new_max2[:, None]), axis=1)\n"
        "        max2 = new_max2\n"
        "\n"
        "        col_start += BLOCK_N\n"
        "\n"
        "    S1 = tl.log(sumexp1) + max1\n"
        "    S2 = tl.log(sumexp2) + max2\n"
        "    tl.store(S1_ptr + rm, S1, mask=mask_rm)\n"
        "    tl.store(S2_ptr + rm, S2, mask=mask_rm)\n"
    )


def _kernel_source_pass2():
    return (
        "@triton.jit\n"
        "def _pass2_jsd_kernel(\n"
        "    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,\n"
        "    S1_ptr, S2_ptr, Out_ptr,\n"
        "    M, N, K,\n"
        "    stride_xm, stride_xk,\n"
        "    stride_w1k, stride_w1n,\n"
        "    stride_w2k, stride_w2n,\n"
        "    stride_b1, stride_b2,\n"
        "    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr\n"
        "):\n"
        "    pid_m = tl.program_id(0)\n"
        "    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n"
        "    mask_rm = rm < M\n"
        "\n"
        "    S1 = tl.load(S1_ptr + rm, mask=mask_rm, other=0.0)\n"
        "    S2 = tl.load(S2_ptr + rm, mask=mask_rm, other=0.0)\n"
        "    S1 = S1[:, None]\n"
        "    S2 = S2[:, None]\n"
        "\n"
        "    rn = tl.arange(0, BLOCK_N)\n"
        "    ln2 = 0.6931471805599453\n"
        "    accum = tl.zeros([BLOCK_M], dtype=tl.float32)\n"
        "\n"
        "    col_start = 0\n"
        "    while col_start < N:\n"
        "        cn = col_start + rn\n"
        "        mask_cn = cn < N\n"
        "\n"
        "        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)\n"
        "        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)\n"
        "\n"
        "        rk = tl.arange(0, BLOCK_K)\n"
        "        k_start = 0\n"
        "        while k_start < K:\n"
        "            kk = k_start + rk\n"
        "            mask_kk = kk < K\n"
        "\n"
        "            x_ptrs = X_ptr + (rm[:, None] * stride_xm + kk[None, :] * stride_xk)\n"
        "            x_tile = tl.load(x_ptrs, mask=mask_rm[:, None] & mask_kk[None, :], other=0.0).to(tl.float16)\n"
        "\n"
        "            w1_ptrs = W1_ptr + (kk[:, None] * stride_w1k + cn[None, :] * stride_w1n)\n"
        "            w2_ptrs = W2_ptr + (kk[:, None] * stride_w2k + cn[None, :] * stride_w2n)\n"
        "            w_mask = mask_kk[:, None] & mask_cn[None, :]\n"
        "\n"
        "            w1_tile = tl.load(w1_ptrs, mask=w_mask, other=0.0)\n"
        "            w2_tile = tl.load(w2_ptrs, mask=w_mask, other=0.0)\n"
        "\n"
        "            acc1 += tl.dot(x_tile, w1_tile)\n"
        "            acc2 += tl.dot(x_tile, w2_tile)\n"
        "\n"
        "            k_start += BLOCK_K\n"
        "\n"
        "        b1 = tl.load(B1_ptr + cn * stride_b1, mask=mask_cn, other=0.0).to(tl.float32)\n"
        "        b2 = tl.load(B2_ptr + cn * stride_b2, mask=mask_cn, other=0.0).to(tl.float32)\n"
        "        acc1 += b1[None, :]\n"
        "        acc2 += b2[None, :]\n"
        "\n"
        "        acc1 = tl.where(mask_cn[None, :], acc1, -float('inf'))\n"
        "        acc2 = tl.where(mask_cn[None, :], acc2, -float('inf'))\n"
        "\n"
        "        logP = acc1 - S1\n"
        "        logQ = acc2 - S2\n"
        "\n"
        "        eP = tl.exp(logP)\n"
        "        eQ = tl.exp(logQ)\n"
        "\n"
        "        mx = tl.maximum(logP, logQ)\n"
        "        sum_exp = tl.exp(logP - mx) + tl.exp(logQ - mx)\n"
        "        logsum = mx + tl.log(sum_exp)\n"
        "        logM = logsum - ln2\n"
        "\n"
        "        contrib = 0.5 * (eP * (logP - logM) + eQ * (logQ - logM))\n"
        "        contrib = tl.where(mask_cn[None, :], contrib, 0.0)\n"
        "        accum += tl.sum(contrib, axis=1)\n"
        "\n"
        "        col_start += BLOCK_N\n"
        "\n"
        "    tl.store(Out_ptr + rm, accum, mask=mask_rm)\n"
    )


def _function_source_fused_linear_jsd():
    return (
        "def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:\n"
        "    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, 'All tensors must be on CUDA'\n"
        "    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16, 'X, W1, W2 must be float16'\n"
        "    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, 'Biases must be float32'\n"
        "    M, K = X.shape\n"
        "    K1, N = W1.shape\n"
        "    K2, N2 = W2.shape\n"
        "    assert K == K1 == K2 and N == N2, 'Shapes must align'\n"
        "    assert B1.shape[0] == N and B2.shape[0] == N, 'Bias shapes must match N'\n"
        "\n"
        "    BLOCK_M = 32\n"
        "    BLOCK_N = 128\n"
        "    BLOCK_K = 32\n"
        "\n"
        "    S1 = torch.empty((M,), device=X.device, dtype=torch.float32)\n"
        "    S2 = torch.empty((M,), device=X.device, dtype=torch.float32)\n"
        "    Out = torch.empty((M,), device=X.device, dtype=torch.float32)\n"
        "\n"
        "    grid = (triton.cdiv(M, BLOCK_M),)\n"
        "\n"
        "    _pass1_logsumexp_kernel[grid](\n"
        "        X, W1, B1, W2, B2,\n"
        "        S1, S2,\n"
        "        M, N, K,\n"
        "        X.stride(0), X.stride(1),\n"
        "        W1.stride(0), W1.stride(1),\n"
        "        W2.stride(0), W2.stride(1),\n"
        "        B1.stride(0), B2.stride(0),\n"
        "        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,\n"
        "        num_warps=8, num_stages=3,\n"
        "    )\n"
        "\n"
        "    _pass2_jsd_kernel[grid](\n"
        "        X, W1, B1, W2, B2,\n"
        "        S1, S2, Out,\n"
        "        M, N, K,\n"
        "        X.stride(0), X.stride(1),\n"
        "        W1.stride(0), W1.stride(1),\n"
        "        W2.stride(0), W2.stride(1),\n"
        "        B1.stride(0), B2.stride(0),\n"
        "        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,\n"
        "        num_warps=8, num_stages=3,\n"
        "    )\n"
        "    return Out\n"
    )


def _solution_reemitter():
    return (
        "class Solution:\n"
        "    def solve(self, spec_path: str = None) -> dict:\n"
        "        return {'code': '\\n'.join([\n"
        "            'import math',\n"
        "            'import torch',\n"
        "            'import triton',\n"
        "            'import triton.language as tl',\n"
        "            '',\n"
        "            " + repr(_kernel_source_pass1().rstrip()) + ",\n"
        "            '',\n"
        "            " + repr(_kernel_source_pass2().rstrip()) + ",\n"
        "            '',\n"
        "            " + repr(_function_source_fused_linear_jsd().rstrip()) + "\n"
        "        ])}\n"
    )
