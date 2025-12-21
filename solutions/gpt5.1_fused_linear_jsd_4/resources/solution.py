import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent('''
import torch
import triton
import triton.language as tl


@triton.jit
def jsd_logits_kernel(
    logits1_ptr, logits2_ptr, out_ptr,
    M, N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    NEG_INF = -1.0e30
    offs_n = tl.arange(0, BLOCK_N)

    # First pass: compute log-sum-exp for each row for both logits
    max1 = NEG_INF
    max2 = NEG_INF
    sum1 = 0.0
    sum2 = 0.0

    for n0 in range(0, N, BLOCK_N):
        idx_n = n0 + offs_n
        mask = idx_n < N

        ptr1 = logits1_ptr + row * stride_l1m + idx_n * stride_l1n
        ptr2 = logits2_ptr + row * stride_l2m + idx_n * stride_l2n

        l1 = tl.load(ptr1, mask=mask, other=NEG_INF)
        l2 = tl.load(ptr2, mask=mask, other=NEG_INF)

        tile_max1 = tl.max(l1, axis=0)
        tile_max2 = tl.max(l2, axis=0)

        new_max1 = tl.maximum(max1, tile_max1)
        new_max2 = tl.maximum(max2, tile_max2)

        sum1 = sum1 * tl.exp(max1 - new_max1) + tl.sum(tl.exp(l1 - new_max1), axis=0)
        sum2 = sum2 * tl.exp(max2 - new_max2) + tl.sum(tl.exp(l2 - new_max2), axis=0)

        max1 = new_max1
        max2 = new_max2

    lse1 = max1 + tl.log(sum1 + 1e-20)
    lse2 = max2 + tl.log(sum2 + 1e-20)

    # Second pass: compute JSD using the precomputed log-sum-exp
    jsd = 0.0
    LOG_EPS = 1e-20

    for n0 in range(0, N, BLOCK_N):
        idx_n = n0 + offs_n
        mask = idx_n < N

        ptr1 = logits1_ptr + row * stride_l1m + idx_n * stride_l1n
        ptr2 = logits2_ptr + row * stride_l2m + idx_n * stride_l2n

        l1 = tl.load(ptr1, mask=mask, other=NEG_INF)
        l2 = tl.load(ptr2, mask=mask, other=NEG_INF)

        s1 = l1 - lse1
        s2 = l2 - lse2

        p = tl.exp(s1)
        q = tl.exp(s2)
        mprob = 0.5 * (p + q)

        logP = s1
        logQ = s2
        logM = tl.log(mprob + LOG_EPS)

        contrib = 0.5 * (p * (logP - logM) + q * (logQ - logM))
        contrib = tl.where(mask, contrib, 0.0)

        jsd += tl.sum(contrib, axis=0)

    tl.store(out_ptr + row, jsd)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)
    
    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    """
    if X.device.type != "cuda":
        raise ValueError("X must be on CUDA device")
    if not (W1.device == X.device == W2.device == B1.device == B2.device):
        raise ValueError("All tensors must be on the same CUDA device")

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    if K1 != K or K2 != K or N2 != N:
        raise ValueError("Incompatible shapes between X and weights")
    if B1.numel() != N or B2.numel() != N:
        raise ValueError("Bias shapes must match output dimension")

    # Compute logits using high-performance cuBLAS GEMM in float16, then upcast to float32
    logits1 = torch.matmul(X, W1).to(torch.float32)
    logits2 = torch.matmul(X, W2).to(torch.float32)

    logits1 += B1
    logits2 += B2

    out = torch.empty(M, device=X.device, dtype=torch.float32)

    stride_l1m, stride_l1n = logits1.stride()
    stride_l2m, stride_l2n = logits2.stride()

    BLOCK_N = 1024
    grid = (M,)

    jsd_logits_kernel[grid](
        logits1, logits2, out,
        M, N,
        stride_l1m, stride_l1n,
        stride_l2m, stride_l2n,
        BLOCK_N=BLOCK_N,
        num_warps=4,
    )

    return out
''')
        return {"code": code}
