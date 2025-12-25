import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Python code for the ragged attention kernel.
        """
        
        ragged_attn_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_N': 32}, num_warps=2, num_stages=1),
        triton.Config({'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=2),
        # Configurations for larger N, potentially more latency-bound
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=2),
        # More aggressive configs
        triton.Config({'BLOCK_N': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=3),
    ],
    key=['N', 'D', 'Dv'],
)
@triton.jit
def _ragged_attn_fwd_kernel(
    Q, K, V, O,
    ROW_LENS,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    '''
    Triton kernel for ragged attention forward pass.
    Each program computes one row of the output tensor O.
    '''
    # Get the program ID, which corresponds to the query row index.
    pid_m = tl.program_id(0)
    
    # Load the specific row length for this query. This is the core of ragged attention.
    row_len = tl.load(ROW_LENS + pid_m)

    # If row_len is 0, there's nothing to compute. Store zeros and exit.
    if row_len == 0:
        o_offs = pid_m * stride_om + tl.arange(0, BLOCK_DV)
        tl.store(O + o_offs, tl.zeros([BLOCK_DV], dtype=O.dtype.element_ty))
        return

    # Pointers to the Q vector for the current row.
    q_offs = pid_m * stride_qm + tl.arange(0, BLOCK_D)
    q = tl.load(Q + q_offs)

    # Initialize accumulator for the output row and softmax statistics.
    # Accumulation is done in float32 for numerical stability.
    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)
    m_i = -float('inf')
    l_i = 0.0
    
    # Attention scale factor.
    scale = (D ** -0.5)
    
    # Loop over the key/value sequence in blocks of BLOCK_N.
    # The loop bound is the dynamic `row_len`, which varies per program.
    for start_n in range(0, row_len, BLOCK_N):
        # -- Load K and V blocks from HBM --
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Pointers to K block.
        k_offs = offs_n[:, None] * stride_kn + tl.arange(0, BLOCK_D)[None, :]
        k_mask = offs_n[:, None] < row_len
        k = tl.load(K + k_offs, mask=k_mask, other=0.0)
        
        # Pointers to V block.
        v_offs = offs_n[:, None] * stride_vn + tl.arange(0, BLOCK_DV)[None, :]
        v_mask = offs_n[:, None] < row_len
        v = tl.load(V + v_offs, mask=v_mask, other=0.0)
        
        # -- Compute attention scores (Q @ K^T) --
        # q is (BLOCK_D,), k is (BLOCK_N, BLOCK_D). Transposing k gives (BLOCK_D, BLOCK_N).
        # The result of the dot product is a (BLOCK_N,) tensor of scores.
        s = tl.dot(q, tl.trans(k), out_dtype=tl.float32)
        s *= scale
        
        # Apply the ragged mask. Scores for j >= row_len should be -inf.
        # This is critical because tl.load with `other=0.0` results in 0-filled vectors for
        # padded elements, leading to a score of 0, not -inf.
        s = tl.where(offs_n < row_len, s, -float('inf'))
        
        # -- Streaming softmax update (numerically stable) --
        # Find the new max score for the current block.
        m_ij = tl.max(s, 0)
        # Correctly update the global max.
        m_new = tl.maximum(m_i, m_ij)
        
        # Rescale the current accumulator and l_i based on the new max.
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha
        l_i = l_i * alpha
        
        # Compute probabilities for the current block and update l_i.
        p = tl.exp(s - m_new)
        l_i += tl.sum(p, 0)
        
        # Update accumulator with new values.
        # Cast p to the value tensor's dtype (float16) to leverage tensor cores.
        acc += tl.dot(p.to(V.dtype.element_ty), v)
        
        # Update the max for the next iteration.
        m_i = m_new

    # -- Finalize and write output --
    # Normalize the accumulator.
    # Guard against division by zero if all scores are -inf (e.g., row_len=0 handled above).
    acc = acc / l_i

    # Write the final output row to HBM.
    o_offs = pid_m * stride_om + tl.arange(0, BLOCK_DV)
    tl.store(O + o_offs, acc.to(O.dtype.element_ty))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape
    
    # Basic input validation.
    assert D == D_k, "Q and K must have the same feature dimension D"
    assert N == N_v, "K and V must have the same sequence length N"
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be on a CUDA device"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"

    # Allocate the output tensor.
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    # The grid is defined by the number of query rows (M).
    # Each program in the grid computes one row of the output.
    grid = (M, )
    
    # Triton kernels often expect int32 for indices and offsets.
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
    
    # Launch the Triton kernel.
    _ragged_attn_fwd_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        BLOCK_D=D,
        BLOCK_DV=Dv
    )
    
    return O
"""
        return {"code": ragged_attn_code}
