import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code_str = r"""
import torch
import triton
import triton.language as tl

# --- Compatibility Shim for GELU ---
# The problem requires using tl.extra.cuda.libdevice.erf.
# In modern Triton versions, this path is deprecated/removed in favor of tl.math.erf.
# We inject a mock structure to satisfy the API requirement if the path is missing.
try:
    _ = tl.extra.cuda.libdevice.erf
except (AttributeError, NameError):
    class MockLibDevice:
        @staticmethod
        def erf(x):
            return tl.math.erf(x)
    class MockCuda:
        libdevice = MockLibDevice
    class MockExtra:
        cuda = MockCuda
    
    # Inject 'extra' into triton.language if needed
    if not hasattr(tl, 'extra'):
        setattr(tl, 'extra', MockExtra)
    # Inject 'cuda' into tl.extra if needed
    elif not hasattr(tl.extra, 'cuda'):
        setattr(tl.extra, 'cuda', MockCuda)
    # Inject 'libdevice' if needed
    elif not hasattr(tl.extra.cuda, 'libdevice'):
        setattr(tl.extra.cuda, 'libdevice', MockLibDevice)

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def get_autotune_configs():
    configs = []
    # Configurations optimized for NVIDIA L4 (Ampere/Ada architecture)
    # Focus on block sizes that map well to Tensor Cores and L2 cache
    stages_list = [3, 4, 5]
    block_m_list = [64, 128, 256]
    block_n_list = [64, 128, 256]
    block_k_list = [32, 64] # Tensor cores prefer K>=16/32
    warps_list = [4, 8]
    
    for num_stages in stages_list:
        for block_m in block_m_list:
            for block_n in block_n_list:
                for block_k in block_k_list:
                    for num_warps in warps_list:
                        # Pruning heuristics
                        # Skip small tiles with many warps
                        if block_m * block_n < 16384 and num_warps == 8:
                            continue
                        # Skip very large tiles that might spill registers or exceed shared mem on some configs
                        if block_m * block_n > 65536: # e.g. 256*256
                            continue
                            
                        configs.append(
                            triton.Config(
                                {
                                    'BLOCK_SIZE_M': block_m, 
                                    'BLOCK_SIZE_N': block_n, 
                                    'BLOCK_SIZE_K': block_k, 
                                    'GROUP_SIZE_M': 8
                                },
                                num_stages=num_stages,
                                num_warps=num_warps
                            )
                        )
    return configs

@triton.autotune(
    configs=get_autotune_configs(),
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(axis=0)
    
    # Block swizzling for better L2 cache locality
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Calculate offsets
    # We use modulo M/N to generate valid indices, but explicit masking in store ensures correctness
    offs_am = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)) % M
    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)) % N
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    # Initial pointers
    # a_ptr points to (M, K), b_ptr points to (K, N)
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # Accumulator (FP32 for precision)
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Main Loop
    # We iterate K in blocks of BLOCK_SIZE_K
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Load tiles
        # We assume shapes are reasonably aligned (step 1024) or we accept slight over-read 
        # (guarded by valid memory allocation or swizzled pointers wrapping safely)
        # For maximum speedup, we avoid masking in the inner loop if possible.
        # However, to ensure K-boundary safety:
        k_remaining = K - k * BLOCK_SIZE_K
        if k_remaining < BLOCK_SIZE_K:
            # Mask needed for the last block of K
            mask_k = offs_k < k_remaining
            a = tl.load(a_ptrs, mask=mask_k[None, :], other=0.0)
            b = tl.load(b_ptrs, mask=mask_k[:, None], other=0.0)
        else:
            # Fast path
            a = tl.load(a_ptrs)
            b = tl.load(b_ptrs)
        
        # Matrix Multiply
        # allow_tf32=True is default/available on Ampere to use Tensor Cores for FP32 inputs
        accumulator += tl.dot(a, b, allow_tf32=True)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Fused Activation (GELU)
    # Applied to FP32 accumulator before cast to output
    c = gelu(accumulator)

    # Store result
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    
    # Boundary check for output
    mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(c_ptrs, c, mask=mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Function to export
    # Check dimensions
    M, K = a.shape
    K_b, N = b.shape
    assert K == K_b, f"Dimension mismatch: {K} != {K_b}"
    
    # Allocate output tensor
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Grid definition
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), 
    )
    
    # Kernel Launch
    fused_matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1)
    )
    
    return c
"""
        return {"code": code_str}
