import torch

FPINT = 32 // 4  # 8 int4 per int32
GROUP = 8
K = FPINT * GROUP  # 64


def _extract_int4(x: torch.Tensor) -> torch.Tensor:
    """
    Unpack 8 signed int4 values from the low 32 bits of int32 tensor x.
    Returns int32 tensor with an extra trailing dim of size 8.
    """
    # x: (...,) int32
    over = (torch.arange(FPINT, device=x.device, dtype=torch.int32) * 4)  # (8,)
    mask = (1 << 4) - 1
    u = (x[..., None] >> over) & mask  # (..., 8) in 0..15
    # Convert to signed int4 (-8..7)
    u = u.to(torch.int32)
    return (u ^ 8) - 8


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    """
    Baseline reference implementation (PyTorch), matches Triton-Puzzles Puzzle 12 semantics.
    Shapes:
      scale: (M, 8) float16/float32
      offset_packed: (M,) int32 (packs 8 int4 offsets)
      weight_packed: (M, 8) int32 (packs 8 int4 weights)
      activation: (64, N) float16
    Returns:
      (M, N) float16
    """
    assert scale.ndim == 2 and scale.shape[1] == FPINT, f"scale must be (M,{FPINT})"
    assert offset_packed.ndim == 1 and offset_packed.shape[0] == scale.shape[0], "offset_packed must be (M,)"
    assert weight_packed.shape == scale.shape and weight_packed.dtype in (torch.int32, torch.int64), "weight_packed must be (M,8) int32/int64"
    assert activation.ndim == 2 and activation.shape[0] == K, f"activation must be ({K}, N)"

    M = scale.shape[0]
    N = activation.shape[1]

    # Unpack weights: (M, 8, 8) -> (M, 64)
    w = _extract_int4(weight_packed.to(torch.int32)).reshape(M, K)

    # Unpack offsets: (M, 8) then expand each offset across GROUP lanes -> (M, 64)
    o = _extract_int4(offset_packed.to(torch.int32)).reshape(M, FPINT)
    o = o[:, :, None].expand(M, FPINT, GROUP).reshape(M, K)

    # Expand scale similarly: (M, 8) -> (M, 64)
    s = scale.to(torch.float32)[:, :, None].expand(M, FPINT, GROUP).reshape(M, K)

    a = s * (w.to(torch.float32) - o.to(torch.float32))  # (M,64) float32
    z = a @ activation.to(torch.float32)  # (M,N) float32
    return z.to(torch.float16)



