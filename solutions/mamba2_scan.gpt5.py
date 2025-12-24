import torch
import triton
import triton.language as tl


@triton.jit
def _chunk_params_kernel(
    X_ptr, A_ptr, B_ptr,
    P_ptr, Q_ptr,
    L, D,
    stride_xl, stride_xd,
    stride_al, stride_ad,
    stride_bl, stride_bd,
    stride_pc, stride_pd,
    stride_qc, stride_qd,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    base_l = pid_c * CHUNK

    y = tl.zeros([BD], dtype=tl.float32)
    p = tl.ones([BD], dtype=tl.float32)

    for t in range(0, CHUNK):
        l_idx = base_l + t
        a = tl.load(A_ptr + l_idx * stride_al + d_offsets * stride_ad, mask=mask_d, other=0).to(tl.float32)
        b = tl.load(B_ptr + l_idx * stride_bl + d_offsets * stride_bd, mask=mask_d, other=0).to(tl.float32)
        x = tl.load(X_ptr + l_idx * stride_xl + d_offsets * stride_xd, mask=mask_d, other=0).to(tl.float32)
        y = a * y + b * x
        p = p * a

    tl.store(P_ptr + pid_c * stride_pc + d_offsets * stride_pd, p, mask=mask_d)
    tl.store(Q_ptr + pid_c * stride_qc + d_offsets * stride_qd, y, mask=mask_d)


@triton.jit
def _chunk_apply_kernel(
    X_ptr, A_ptr, B_ptr,
    Y_ptr, Yinit_ptr,
    L, D,
    stride_xl, stride_xd,
    stride_al, stride_ad,
    stride_bl, stride_bd,
    stride_yl, stride_yd,
    stride_ic, stride_id,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    base_l = pid_c * CHUNK

    y = tl.load(Yinit_ptr + pid_c * stride_ic + d_offsets * stride_id, mask=mask_d, other=0.0).to(tl.float32)

    for t in range(0, CHUNK):
        l_idx = base_l + t
        a = tl.load(A_ptr + l_idx * stride_al + d_offsets * stride_ad, mask=mask_d, other=0).to(tl.float32)
        b = tl.load(B_ptr + l_idx * stride_bl + d_offsets * stride_bd, mask=mask_d, other=0).to(tl.float32)
        x = tl.load(X_ptr + l_idx * stride_xl + d_offsets * stride_xd, mask=mask_d, other=0).to(tl.float32)
        y = a * y + b * x
        tl.store(Y_ptr + l_idx * stride_yl + d_offsets * stride_yd, y.to(tl.float16), mask=mask_d)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be on CUDA"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert X.shape == A.shape == B.shape
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"

    C = L // chunk
    device = X.device

    # Allocate per-chunk parameters and initial states
    P = torch.empty((C, D), dtype=torch.float32, device=device)
    Q = torch.empty((C, D), dtype=torch.float32, device=device)

    grid = (C, triton.cdiv(D, BD))

    _chunk_params_kernel[grid](
        X, A, B,
        P, Q,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        P.stride(0), P.stride(1),
        Q.stride(0), Q.stride(1),
        CHUNK=chunk, BD=BD,
        num_warps=4, num_stages=2,
    )

    # Compute initial state for each chunk via sequential composition on GPU
    Yinit = torch.empty((C, D), dtype=torch.float32, device=device)
    acc = torch.zeros((D,), dtype=torch.float32, device=device)
    for ci in range(C):
        Yinit[ci].copy_(acc)
        acc = P[ci] * acc + Q[ci]

    # Second pass: compute outputs per chunk
    Y = torch.empty((L, D), dtype=torch.float16, device=device)
    _chunk_apply_kernel[grid](
        X, A, B,
        Y, Yinit,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        Yinit.stride(0), Yinit.stride(1),
        CHUNK=chunk, BD=BD,
        num_warps=4, num_stages=3,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            "@triton.jit\n"
            "def _chunk_params_kernel(\n"
            "    X_ptr, A_ptr, B_ptr,\n"
            "    P_ptr, Q_ptr,\n"
            "    L, D,\n"
            "    stride_xl, stride_xd,\n"
            "    stride_al, stride_ad,\n"
            "    stride_bl, stride_bd,\n"
            "    stride_pc, stride_pd,\n"
            "    stride_qc, stride_qd,\n"
            "    CHUNK: tl.constexpr,\n"
            "    BD: tl.constexpr,\n"
            "):\n"
            "    pid_c = tl.program_id(0)\n"
            "    pid_d = tl.program_id(1)\n\n"
            "    d_offsets = pid_d * BD + tl.arange(0, BD)\n"
            "    mask_d = d_offsets < D\n\n"
            "    base_l = pid_c * CHUNK\n\n"
            "    y = tl.zeros([BD], dtype=tl.float32)\n"
            "    p = tl.ones([BD], dtype=tl.float32)\n\n"
            "    for t in range(0, CHUNK):\n"
            "        l_idx = base_l + t\n"
            "        a = tl.load(A_ptr + l_idx * stride_al + d_offsets * stride_ad, mask=mask_d, other=0).to(tl.float32)\n"
            "        b = tl.load(B_ptr + l_idx * stride_bl + d_offsets * stride_bd, mask=mask_d, other=0).to(tl.float32)\n"
            "        x = tl.load(X_ptr + l_idx * stride_xl + d_offsets * stride_xd, mask=mask_d, other=0).to(tl.float32)\n"
            "        y = a * y + b * x\n"
            "        p = p * a\n"
            "    tl.store(P_ptr + pid_c * stride_pc + d_offsets * stride_pd, p, mask=mask_d)\n"
            "    tl.store(Q_ptr + pid_c * stride_qc + d_offsets * stride_qd, y, mask=mask_d)\n\n"
            "@triton.jit\n"
            "def _chunk_apply_kernel(\n"
            "    X_ptr, A_ptr, B_ptr,\n"
            "    Y_ptr, Yinit_ptr,\n"
            "    L, D,\n"
            "    stride_xl, stride_xd,\n"
            "    stride_al, stride_ad,\n"
            "    stride_bl, stride_bd,\n"
            "    stride_yl, stride_yd,\n"
            "    stride_ic, stride_id,\n"
            "    CHUNK: tl.constexpr,\n"
            "    BD: tl.constexpr,\n"
            "):\n"
            "    pid_c = tl.program_id(0)\n"
            "    pid_d = tl.program_id(1)\n\n"
            "    d_offsets = pid_d * BD + tl.arange(0, BD)\n"
            "    mask_d = d_offsets < D\n"
            "    base_l = pid_c * CHUNK\n"
            "    y = tl.load(Yinit_ptr + pid_c * stride_ic + d_offsets * stride_id, mask=mask_d, other=0.0).to(tl.float32)\n"
            "    for t in range(0, CHUNK):\n"
            "        l_idx = base_l + t\n"
            "        a = tl.load(A_ptr + l_idx * stride_al + d_offsets * stride_ad, mask=mask_d, other=0).to(tl.float32)\n"
            "        b = tl.load(B_ptr + l_idx * stride_bl + d_offsets * stride_bd, mask=mask_d, other=0).to(tl.float32)\n"
            "        x = tl.load(X_ptr + l_idx * stride_xl + d_offsets * stride_xd, mask=mask_d, other=0).to(tl.float32)\n"
            "        y = a * y + b * x\n"
            "        tl.store(Y_ptr + l_idx * stride_yl + d_offsets * stride_yd, y.to(tl.float16), mask=mask_d)\n\n"
            "def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:\n"
            "    assert X.is_cuda and A.is_cuda and B.is_cuda, 'Inputs must be on CUDA'\n"
            "    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16\n"
            "    assert X.shape == A.shape == B.shape\n"
            "    L, D = X.shape\n"
            "    assert L % chunk == 0, 'L must be divisible by chunk'\n"
            "    C = L // chunk\n"
            "    device = X.device\n"
            "    P = torch.empty((C, D), dtype=torch.float32, device=device)\n"
            "    Q = torch.empty((C, D), dtype=torch.float32, device=device)\n"
            "    grid = (C, triton.cdiv(D, BD))\n"
            "    _chunk_params_kernel[grid](\n"
            "        X, A, B,\n"
            "        P, Q,\n"
            "        L, D,\n"
            "        X.stride(0), X.stride(1),\n"
            "        A.stride(0), A.stride(1),\n"
            "        B.stride(0), B.stride(1),\n"
            "        P.stride(0), P.stride(1),\n"
            "        Q.stride(0), Q.stride(1),\n"
            "        CHUNK=chunk, BD=BD,\n"
            "        num_warps=4, num_stages=2,\n"
            "    )\n"
            "    Yinit = torch.empty((C, D), dtype=torch.float32, device=device)\n"
            "    acc = torch.zeros((D,), dtype=torch.float32, device=device)\n"
            "    for ci in range(C):\n"
            "        Yinit[ci].copy_(acc)\n"
            "        acc = P[ci] * acc + Q[ci]\n"
            "    Y = torch.empty((L, D), dtype=torch.float16, device=device)\n"
            "    _chunk_apply_kernel[grid](\n"
            "        X, A, B,\n"
            "        Y, Yinit,\n"
            "        L, D,\n"
            "        X.stride(0), X.stride(1),\n"
            "        A.stride(0), A.stride(1),\n"
            "        B.stride(0), B.stride(1),\n"
            "        Y.stride(0), Y.stride(1),\n"
            "        Yinit.stride(0), Yinit.stride(1),\n"
            "        CHUNK=chunk, BD=BD,\n"
            "        num_warps=4, num_stages=3,\n"
            "    )\n"
            "    return Y\n"
        )
        return {"code": code}
