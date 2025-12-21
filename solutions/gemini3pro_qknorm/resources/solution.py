import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _qknorm_kernel(
    Q_ptr, K_ptr, W_ptr,
    Q_out_ptr, K_out_ptr,
    qs0, qs1, qs2, qs3,
    ks0, ks1, ks2, ks3,
    q_stride_d, k_stride_d,
    q_sh0, q_sh1, q_sh2, q_sh3,
    k_sh0, k_sh1, k_sh2, k_sh3,
    N_q, N_k, D,
    eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Offsets
    offs = tl.arange(0, BLOCK_SIZE)
    mask = offs < D

    # Weight load
    w = tl.load(W_ptr + offs, mask=mask, other=0.0).to(tl.float32)

    # Pointers placeholders
    curr_ptr = Q_ptr
    curr_out_ptr = Q_out_ptr
    stride_d = 0
    
    # Branch for Q or K
    if pid < N_q:
        idx = pid
        # Index unravelling for Q (Row Major)
        # 4 dimensions
        r3 = idx % q_sh3; idx = idx // q_sh3
        r2 = idx % q_sh2; idx = idx // q_sh2
        r1 = idx % q_sh1
        r0 = idx // q_sh1
        
        offset = r0 * qs0 + r1 * qs1 + r2 * qs2 + r3 * qs3
        curr_ptr = Q_ptr + offset
        curr_out_ptr = Q_out_ptr + pid * D
        stride_d = q_stride_d
    else:
        idx = pid - N_q
        # Index unravelling for K
        r3 = idx % k_sh3; idx = idx // k_sh3
        r2 = idx % k_sh2; idx = idx // k_sh2
        r1 = idx % k_sh1
        r0 = idx // k_sh1
        
        offset = r0 * ks0 + r1 * ks1 + r2 * ks2 + r3 * ks3
        curr_ptr = K_ptr + offset
        curr_out_ptr = K_out_ptr + (pid - N_q) * D
        stride_d = k_stride_d

    # Load and Normalize
    # Handle potentially non-contiguous last dimension
    x_ptrs = curr_ptr + offs * stride_d
    x = tl.load(x_ptrs, mask=mask, other=0.0).to(tl.float32)
    
    x_sq = x * x
    mean_sq = tl.sum(x_sq, axis=0) / D
    rstd = tl.rsqrt(mean_sq + eps)
    
    out = x * rstd * w
    
    # Store output (contiguous)
    tl.store(curr_out_ptr + offs, out, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors using a fused Triton kernel.
    Handles non-contiguous inputs efficiently.
    """
    q_shape = q.shape
    k_shape = k.shape
    D = q_shape[-1]
    
    # Helper to prepare packed shapes/strides
    def get_params(t):
        shape = list(t.shape[:-1])
        strides = list(t.stride()[:-1])
        stride_d = t.stride(-1)
        
        # Collapse contiguous dimensions to reduce indexing overhead
        i = 0
        while i < len(shape) - 1:
            if strides[i] == strides[i+1] * shape[i+1]:
                shape[i] *= shape[i+1]
                shape.pop(i+1)
                strides.pop(i+1)
            else:
                i += 1
        
        # Pad to 4 batch dimensions
        while len(shape) < 4:
            shape.insert(0, 1)
            strides.insert(0, 0)
            
        return shape, strides, stride_d

    qs, qst, qsd = get_params(q)
    ks, kst, ksd = get_params(k)
    
    N_q = 1
    for s in qs: N_q *= s
    N_k = 1
    for s in ks: N_k *= s
    
    # Allocate contiguous outputs
    q_o = torch.empty(q_shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k_shape, device=k.device, dtype=k.dtype)
    
    total_rows = N_q + N_k
    BLOCK_SIZE = triton.next_power_of_2(D)
    if BLOCK_SIZE < 128: BLOCK_SIZE = 128
    
    grid = (total_rows,)
    
    _qknorm_kernel[grid](
        q, k, norm_weight,
        q_o, k_o,
        qst[0], qst[1], qst[2], qst[3],
        kst[0], kst[1], kst[2], kst[3],
        qsd, ksd,
        qs[0], qs[1], qs[2], qs[3],
        ks[0], ks[1], ks[2], ks[3],
        N_q, N_k, D,
        1e-6,
        BLOCK_SIZE=BLOCK_SIZE
    )
    
    return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect
        code = inspect.getsource(qknorm)
        # Also need the kernel source
        kernel_code = inspect.getsource(_qknorm_kernel)
        imports = "import torch\nimport triton\nimport triton.language as tl\nimport flashinfer\n"
        full_code = imports + kernel_code + "\n" + code
        return {"code": full_code}
