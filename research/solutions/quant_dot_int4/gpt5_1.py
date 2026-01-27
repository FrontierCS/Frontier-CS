import torch
import triton
import triton.language as tl


FPINT = 8
GROUP = 8
K_CONST = FPINT * GROUP


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256}, num_warps=8, num_stages=2),
    ],
    key=["M", "N"],
)
@triton.jit
def _quant_dot_kernel(
    scale_ptr,  # (M, 8) float16/float32
    off_ptr,    # (M,) int32 packed 8x int4 offsets
    w_ptr,      # (M, 8) int32 packed 8x int4 weights
    act_ptr,    # (64, N) float16
    out_ptr,    # (M, N) float16
    M: tl.constexpr,
    N: tl.constexpr,
    scale_stride_m, scale_stride_t,
    off_stride_m,
    w_stride_m, w_stride_t,
    act_stride_k, act_stride_n,
    out_stride_m, out_stride_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    # Row/col indices for this program
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mmask = rm < M
    nmask = rn < N

    # Preload activation tile (K=64 x BLOCK_N)
    k_range = tl.arange(0, K_CONST)
    # Load activation rows as fp32 for compute
    act_tile = tl.load(
        act_ptr + k_range[:, None] * act_stride_k + rn[None, :] * act_stride_n,
        mask=nmask[None, :],
        other=0.0,
    )
    act_tile = act_tile.to(tl.float32)

    # Prepare accumulators
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Load packed offsets for each row
    off32 = tl.load(off_ptr + rm * off_stride_m, mask=mmask, other=0).to(tl.int32)

    # Preload scales for f in [0..7]
    # scale shape: (M, 8) along t dimension interpreted as per-FPINT (f) scales.
    # We'll store as float32 for compute.
    # Build pointers to each f
    # scale_ptr_f = scale_ptr + rm[:,None]*scale_stride_m + f[None,:]*scale_stride_t
    f_idx = tl.arange(0, FPINT)
    scale_mat = tl.load(
        scale_ptr + rm[:, None] * scale_stride_m + f_idx[None, :] * scale_stride_t,
        mask=mmask[:, None],
        other=0.0,
    )
    scale_mat = scale_mat.to(tl.float32)  # (BLOCK_M, 8)

    # Main compute loops
    # Iterate groups g (which selects which int32 across K/8) and nibble f
    # weight_ptr for group g is (rm * w_stride_m + g*w_stride_t)
    for g in range(GROUP):
        w32g = tl.load(w_ptr + rm * w_stride_m + g * w_stride_t, mask=mmask, other=0).to(tl.int32)
        for f in range(FPINT):
            # Extract int4 nibble for weights and offsets
            shift = f * 4
            w_nib = (w32g >> shift) & 0xF
            o_nib = (off32 >> shift) & 0xF

            # Convert to float32
            w_val = w_nib.to(tl.float32)
            o_val = o_nib.to(tl.float32)

            # Select scale for f: shape (BLOCK_M,)
            s_val = scale_mat[:, f]

            # Dequantized vector for this k
            deq = s_val * (w_val - o_val)  # (BLOCK_M,)

            # Activation row k = g*8 + f
            k = g * FPINT + f
            act_row = act_tile[k, :]  # (BLOCK_N,)

            # Accumulate outer product: deq[:,None] * act_row[None,:]
            acc += deq[:, None] * act_row[None, :]

    # Store result (cast to fp16)
    out = acc.to(tl.float16)
    tl.store(out_ptr + rm[:, None] * out_stride_m + rn[None, :] * out_stride_n, out, mask=mmask[:, None] & nmask[None, :])


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    """
    Args:
        scale: float16/float32 tensor of shape (M, K/8)
        offset_packed: int32 tensor of shape (M,)
        weight_packed: int32 tensor of shape (M, K/8)
        activation: float16 tensor of shape (K, N)
    Returns:
        Output tensor of shape (M, N), dtype float16
    """
    assert activation.is_cuda and weight_packed.is_cuda and offset_packed.is_cuda and scale.is_cuda
    assert activation.dtype == torch.float16
    assert weight_packed.dtype == torch.int32
    assert offset_packed.dtype == torch.int32
    assert scale.dtype in (torch.float16, torch.float32)

    M = weight_packed.shape[0]
    K = activation.shape[0]
    N = activation.shape[1]
    assert K == K_CONST, f"K must be {K_CONST} but got {K}"
    assert scale.shape[0] == M and scale.shape[1] == FPINT, "scale must have shape (M, 8)"
    assert weight_packed.shape[1] == GROUP, "weight_packed must have shape (M, 8)"
    assert offset_packed.shape[0] == M

    # Allocate output
    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    # Extract strides
    scale_s0, scale_s1 = scale.stride()
    # When using non-contiguous scale we need strides in element units
    off_s0 = offset_packed.stride(0)

    w_s0, w_s1 = weight_packed.stride()

    act_s0, act_s1 = activation.stride()
    out_s0, out_s1 = out.stride()

    # Launch kernel
    grid = (
        triton.cdiv(M, 64),  # default BLOCK_M from autotune largest; grid will be overridden by JIT meta
        triton.cdiv(N, 128),
    )
    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, out,
        M, N,
        scale_s0, scale_s1,
        off_s0,
        w_s0, w_s1,
        act_s0, act_s1,
        out_s0, out_s1,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect
        src = inspect.getsource(quant_dot)
        # Need also the kernel and imports; reconstruct full module code
        module_code = []
        module_code.append("import torch")
        module_code.append("import triton")
        module_code.append("import triton.language as tl")
        module_code.append(f"FPINT = {FPINT}")
        module_code.append(f"GROUP = {GROUP}")
        module_code.append(f"K_CONST = {K_CONST}")
        # Add kernel source
        module_code.append(inspect.getsource(_quant_dot_kernel))
        # Add function source
        module_code.append(inspect.getsource(quant_dot))
        # Add Solution class stub (not necessary in evaluated module, but keep minimal)
        full_code = "\n\n".join(module_code)
        return {"code": full_code}