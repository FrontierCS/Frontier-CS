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
def _forward_zero_kernel(
    X_ptr, A_ptr, B_ptr,
    Y_ptr, Pprefix_ptr,
    Pchunk_ptr, Yend_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    stride_pp_l, stride_pp_d,
    stride_pc_c, stride_pc_d,
    stride_ye_c, stride_ye_d,
    CHUNK: tl.constexpr, BD: tl.constexpr
):
    pid_d = tl.program_id(axis=0)
    pid_c = tl.program_id(axis=1)

    col_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = col_offsets < D

    start_l = pid_c * CHUNK

    y_prev = tl.zeros([BD], dtype=tl.float32)
    p_prev = tl.ones([BD], dtype=tl.float32)

    # Loop over timesteps within the chunk
    for t in range(0, CHUNK):
        row = start_l + t

        a = tl.load(A_ptr + row * stride_a_l + col_offsets * stride_a_d, mask=mask_d, other=0.).to(tl.float32)
        b = tl.load(B_ptr + row * stride_b_l + col_offsets * stride_b_d, mask=mask_d, other=0.).to(tl.float32)
        x = tl.load(X_ptr + row * stride_x_l + col_offsets * stride_x_d, mask=mask_d, other=0.).to(tl.float32)

        y_prev = a * y_prev + b * x
        p_prev = p_prev * a

        # store outputs for this timestep
        tl.store(Y_ptr + row * stride_y_l + col_offsets * stride_y_d, y_prev.to(tl.float16), mask=mask_d)
        tl.store(Pprefix_ptr + row * stride_pp_l + col_offsets * stride_pp_d, p_prev.to(tl.float16), mask=mask_d)

    # store per-chunk summaries
    tl.store(Pchunk_ptr + pid_c * stride_pc_c + col_offsets * stride_pc_d, p_prev.to(tl.float16), mask=mask_d)
    tl.store(Yend_ptr + pid_c * stride_ye_c + col_offsets * stride_ye_d, y_prev.to(tl.float16), mask=mask_d)


@triton.jit
def _scan_chunk_states_kernel(
    Pchunk_ptr, Yend_ptr, Sstart_ptr,
    C, D,
    stride_pc_c, stride_pc_d,
    stride_ye_c, stride_ye_d,
    stride_ss_c, stride_ss_d,
    BD: tl.constexpr
):
    pid_d = tl.program_id(axis=0)
    col_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = col_offsets < D

    s_prev = tl.zeros([BD], dtype=tl.float32)

    for k in range(0, C):
        # Sstart[k] = s_prev
        tl.store(Sstart_ptr + k * stride_ss_c + col_offsets * stride_ss_d, s_prev.to(tl.float16), mask=mask_d)

        p = tl.load(Pchunk_ptr + k * stride_pc_c + col_offsets * stride_pc_d, mask=mask_d, other=0.).to(tl.float32)
        y_end0 = tl.load(Yend_ptr + k * stride_ye_c + col_offsets * stride_ye_d, mask=mask_d, other=0.).to(tl.float32)
        s_prev = y_end0 + p * s_prev


@triton.jit
def _apply_correction_kernel(
    Y_ptr, Pprefix_ptr, Sstart_ptr,
    L, D,
    stride_y_l, stride_y_d,
    stride_pp_l, stride_pp_d,
    stride_ss_c, stride_ss_d,
    CHUNK: tl.constexpr, BD: tl.constexpr
):
    pid_d = tl.program_id(axis=0)
    pid_c = tl.program_id(axis=1)

    col_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = col_offsets < D

    s_start = tl.load(Sstart_ptr + pid_c * stride_ss_c + col_offsets * stride_ss_d, mask=mask_d, other=0.).to(tl.float32)
    base_l = pid_c * CHUNK

    for t in range(0, CHUNK):
        row = base_l + t
        pp = tl.load(Pprefix_ptr + row * stride_pp_l + col_offsets * stride_pp_d, mask=mask_d, other=0.).to(tl.float32)
        y0 = tl.load(Y_ptr + row * stride_y_l + col_offsets * stride_y_d, mask=mask_d, other=0.).to(tl.float32)
        y = y0 + pp * s_start
        tl.store(Y_ptr + row * stride_y_l + col_offsets * stride_y_d, y.to(tl.float16), mask=mask_d)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    
    Args:
        X: Input tensor of shape (L, D) - input sequence (float16)
        A: Input tensor of shape (L, D) - decay factors (float16)
        B: Input tensor of shape (L, D) - input weights (float16)
        chunk: Chunk size for parallel processing (default 128)
        BD: Block dimension for feature dimension tiling (default 128)
    
    Returns:
        Output tensor of shape (L, D) - scan output (float16)
    """
    assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be on CUDA"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
    assert X.shape == A.shape == B.shape, "X, A, B must have same shape"
    L, D = X.shape
    assert chunk > 0 and L % chunk == 0, "L must be divisible by chunk"
    C = L // chunk

    # Prepare output and temporary buffers
    Y = torch.empty_like(X)
    Pprefix = torch.empty_like(X)  # per-timestep prefix product within chunk
    Pchunk = torch.empty((C, D), device=X.device, dtype=torch.float16)  # per-chunk product of a
    Yend0 = torch.empty((C, D), device=X.device, dtype=torch.float16)   # per-chunk end y with zero init
    Sstart = torch.empty((C, D), device=X.device, dtype=torch.float16)  # per-chunk starting state

    # Compute strides in elements
    stride_x_l, stride_x_d = X.stride()
    stride_a_l, stride_a_d = A.stride()
    stride_b_l, stride_b_d = B.stride()
    stride_y_l, stride_y_d = Y.stride()
    stride_pp_l, stride_pp_d = Pprefix.stride()
    stride_pc_c, stride_pc_d = Pchunk.stride()
    stride_ye_c, stride_ye_d = Yend0.stride()
    stride_ss_c, stride_ss_d = Sstart.stride()

    # Kernel launch configs
    grid0 = (triton.cdiv(D, BD), C)
    _forward_zero_kernel[grid0](
        X, A, B,
        Y, Pprefix,
        Pchunk, Yend0,
        L, D,
        stride_x_l, stride_x_d,
        stride_a_l, stride_a_d,
        stride_b_l, stride_b_d,
        stride_y_l, stride_y_d,
        stride_pp_l, stride_pp_d,
        stride_pc_c, stride_pc_d,
        stride_ye_c, stride_ye_d,
        CHUNK=chunk, BD=BD,
        num_warps=4, num_stages=2
    )

    grid1 = (triton.cdiv(D, BD),)
    _scan_chunk_states_kernel[grid1](
        Pchunk, Yend0, Sstart,
        C, D,
        stride_pc_c, stride_pc_d,
        stride_ye_c, stride_ye_d,
        stride_ss_c, stride_ss_d,
        BD=BD,
        num_warps=4, num_stages=2
    )

    grid2 = (triton.cdiv(D, BD), C)
    _apply_correction_kernel[grid2](
        Y, Pprefix, Sstart,
        L, D,
        stride_y_l, stride_y_d,
        stride_pp_l, stride_pp_d,
        stride_ss_c, stride_ss_d,
        CHUNK=chunk, BD=BD,
        num_warps=4, num_stages=2
    )

    return Y
'''
        return {"code": code}
