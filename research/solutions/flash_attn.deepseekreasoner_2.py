import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'Dq'],
)
@triton.jit
def _flash_attn_forward_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_z = tl.program_id(2)
    
    start_m = pid_m * BLOCK_M
    start_n = 0
    
    q_offset = pid_z * stride_qz + pid_h * stride_qh + start_m * stride_qm
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    o_offset = pid_z * stride_oz + pid_h * stride_oh + start_m * stride_om
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    q_ptrs = tl.make_block_ptr(
        base=Q,
        shape=(M, Dq),
        strides=(stride_qm, stride_qd),
        offsets=(start_m, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    k_ptrs = tl.make_block_ptr(
        base=K,
        shape=(N, Dq),
        strides=(stride_kn, stride_kd),
        offsets=(0, 0),
        block_shape=(BLOCK_N, BLOCK_D),
        order=(1, 0)
    )
    
    v_ptrs = tl.make_block_ptr(
        base=V,
        shape=(N, Dv),
        strides=(stride_vn, stride_vd),
        offsets=(0, 0),
        block_shape=(BLOCK_N, BLOCK_D),
        order=(1, 0)
    )
    
    for start_n in range(0, N, BLOCK_N):
        q = tl.load(q_ptrs, boundary_check=(0, 1))
        k = tl.load(k_ptrs, boundary_check=(0, 1))
        v = tl.load(v_ptrs, boundary_check=(0, 1))
        
        q = q.to(tl.float32)
        k = k.to(tl.float32)
        
        s = tl.dot(q, tl.trans(k), allow_tf32=False) * (1.0 / tl.sqrt(Dq))
        
        if causal:
            m = start_m + tl.arange(0, BLOCK_M)
            n = start_n + tl.arange(0, BLOCK_N)
            mask = m[:, None] >= n[None, :]
            s = tl.where(mask, s, float('-inf'))
        
        m_ij = tl.maximum(m_i[:, None], tl.max(s, axis=1))
        p = tl.exp(s - m_ij)
        l_ij = tl.exp(m_i[:, None] - m_ij) * l_i[:, None] + tl.sum(p, axis=1)
        
        alpha = tl.exp(m_i[:, None] - m_ij) / l_ij
        acc = acc * alpha[:, None]
        
        p = p / l_ij[:, None]
        acc = acc + tl.dot(p.to(v.dtype), v, allow_tf32=False)
        
        m_i = m_ij
        l_i = l_ij
        
        k_ptrs = tl.advance(k_ptrs, (BLOCK_N, 0))
        v_ptrs = tl.advance(v_ptrs, (BLOCK_N, 0))
    
    o = acc.to(O.dtype.element_ty)
    
    o_ptrs = tl.make_block_ptr(
        base=O,
        shape=(M, Dv),
        strides=(stride_om, stride_od),
        offsets=(start_m, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    tl.store(o_ptrs, o, boundary_check=(0, 1))


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (triton.cdiv(M, 128), H, Z)
    
    _flash_attn_forward_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        causal,
        BLOCK_M=128, BLOCK_N=64, BLOCK_D=64
    )
    
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": "import torch\nimport triton\nimport triton.language as tl\n\n" + 
                "### TRITON KERNEL ###\n" + 
                "@triton.autotune(\n" + 
                "    configs=[\n" + 
                "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=4),\n" + 
                "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=4),\n" + 
                "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=4),\n" + 
                "        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),\n" + 
                "        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=2, num_warps=8),\n" + 
                "    ],\n" + 
                "    key=['M', 'N', 'Dq'],\n" + 
                ")\n" + 
                "@triton.jit\n" + 
                "def _flash_attn_forward_kernel(\n" + 
                "    Q, K, V, O,\n" + 
                "    stride_qz, stride_qh, stride_qm, stride_qd,\n" + 
                "    stride_kz, stride_kh, stride_kn, stride_kd,\n" + 
                "    stride_vz, stride_vh, stride_vn, stride_vd,\n" + 
                "    stride_oz, stride_oh, stride_om, stride_od,\n" + 
                "    Z, H, M, N, Dq, Dv,\n" + 
                "    causal: tl.constexpr,\n" + 
                "    BLOCK_M: tl.constexpr,\n" + 
                "    BLOCK_N: tl.constexpr,\n" + 
                "    BLOCK_D: tl.constexpr,\n" + 
                "):\n" + 
                "    pid_m = tl.program_id(0)\n" + 
                "    pid_h = tl.program_id(1)\n" + 
                "    pid_z = tl.program_id(2)\n" + 
                "    \n" + 
                "    start_m = pid_m * BLOCK_M\n" + 
                "    start_n = 0\n" + 
                "    \n" + 
                "    q_offset = pid_z * stride_qz + pid_h * stride_qh + start_m * stride_qm\n" + 
                "    k_offset = pid_z * stride_kz + pid_h * stride_kh\n" + 
                "    v_offset = pid_z * stride_vz + pid_h * stride_vh\n" + 
                "    o_offset = pid_z * stride_oz + pid_h * stride_oh + start_m * stride_om\n" + 
                "    \n" + 
                "    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')\n" + 
                "    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)\n" + 
                "    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)\n" + 
                "    \n" + 
                "    q_ptrs = tl.make_block_ptr(\n" + 
                "        base=Q,\n" + 
                "        shape=(M, Dq),\n" + 
                "        strides=(stride_qm, stride_qd),\n" + 
                "        offsets=(start_m, 0),\n" + 
                "        block_shape=(BLOCK_M, BLOCK_D),\n" + 
                "        order=(1, 0)\n" + 
                "    )\n" + 
                "    \n" + 
                "    k_ptrs = tl.make_block_ptr(\n" + 
                "        base=K,\n" + 
                "        shape=(N, Dq),\n" + 
                "        strides=(stride_kn, stride_kd),\n" + 
                "        offsets=(0, 0),\n" + 
                "        block_shape=(BLOCK_N, BLOCK_D),\n" + 
                "        order=(1, 0)\n" + 
                "    )\n" + 
                "    \n" + 
                "    v_ptrs = tl.make_block_ptr(\n" + 
                "        base=V,\n" + 
                "        shape=(N, Dv),\n" + 
                "        strides=(stride_vn, stride_vd),\n" + 
                "        offsets=(0, 0),\n" + 
                "        block_shape=(BLOCK_N, BLOCK_D),\n" + 
                "        order=(1, 0)\n" + 
                "    )\n" + 
                "    \n" + 
                "    for start_n in range(0, N, BLOCK_N):\n" + 
                "        q = tl.load(q_ptrs, boundary_check=(0, 1))\n" + 
                "        k = tl.load(k_ptrs, boundary_check=(0, 1))\n" + 
                "        v = tl.load(v_ptrs, boundary_check=(0, 1))\n" + 
                "        \n" + 
                "        q = q.to(tl.float32)\n" + 
                "        k = k.to(tl.float32)\n" + 
                "        \n" + 
                "        s = tl.dot(q, tl.trans(k), allow_tf32=False) * (1.0 / tl.sqrt(Dq))\n" + 
                "        \n" + 
                "        if causal:\n" + 
                "            m = start_m + tl.arange(0, BLOCK_M)\n" + 
                "            n = start_n + tl.arange(0, BLOCK_N)\n" + 
                "            mask = m[:, None] >= n[None, :]\n" + 
                "            s = tl.where(mask, s, float('-inf'))\n" + 
                "        \n" + 
                "        m_ij = tl.maximum(m_i[:, None], tl.max(s, axis=1))\n" + 
                "        p = tl.exp(s - m_ij)\n" + 
                "        l_ij = tl.exp(m_i[:, None] - m_ij) * l_i[:, None] + tl.sum(p, axis=1)\n" + 
                "        \n" + 
                "        alpha = tl.exp(m_i[:, None] - m_ij) / l_ij\n" + 
                "        acc = acc * alpha[:, None]\n" + 
                "        \n" + 
                "        p = p / l_ij[:, None]\n" + 
                "        acc = acc + tl.dot(p.to(v.dtype), v, allow_tf32=False)\n" + 
                "        \n" + 
                "        m_i = m_ij\n" + 
                "        l_i = l_ij\n" + 
                "        \n" + 
                "        k_ptrs = tl.advance(k_ptrs, (BLOCK_N, 0))\n" + 
                "        v_ptrs = tl.advance(v_ptrs, (BLOCK_N, 0))\n" + 
                "    \n" + 
                "    o = acc.to(O.dtype.element_ty)\n" + 
                "    \n" + 
                "    o_ptrs = tl.make_block_ptr(\n" + 
                "        base=O,\n" + 
                "        shape=(M, Dv),\n" + 
                "        strides=(stride_om, stride_od),\n" + 
                "        offsets=(start_m, 0),\n" + 
                "        block_shape=(BLOCK_M, BLOCK_D),\n" + 
                "        order=(1, 0)\n" + 
                "    )\n" + 
                "    \n" + 
                "    tl.store(o_ptrs, o, boundary_check=(0, 1))\n" + 
                "\n" + 
                "### WRAPPER FUNCTION ###\n" + 
                "def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:\n" + 
                "    Z, H, M, Dq = Q.shape\n" + 
                "    _, _, N, Dv = V.shape\n" + 
                "    \n" + 
                "    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)\n" + 
                "    \n" + 
                "    grid = (triton.cdiv(M, 128), H, Z)\n" + 
                "    \n" + 
                "    _flash_attn_forward_kernel[grid](\n" + 
                "        Q, K, V, O,\n" + 
                "        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),\n" + 
                "        K.stride(0), K.stride(1), K.stride(2), K.stride(3),\n" + 
                "        V.stride(0), V.stride(1), V.stride(2), V.stride(3),\n" + 
                "        O.stride(0), O.stride(1), O.stride(2), O.stride(3),\n" + 
                "        Z, H, M, N, Dq, Dv,\n" + 
                "        causal,\n" + 
                "        BLOCK_M=128, BLOCK_N=64, BLOCK_D=64\n" + 
                "    )\n" + 
                "    \n" + 
                "    return O\n" + 
                "\n" + 
                "### SOLUTION CLASS ###\n" + 
                "class Solution:\n" + 
                "    def solve(self, spec_path: str = None) -> dict:\n" + 
                "        return {'code': 'Complete implementation is already in memory'}"}