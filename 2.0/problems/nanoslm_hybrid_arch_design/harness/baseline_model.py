"""Baseline Transformer Architecture. CUDA-only, like everything scored here.

A plain-PyTorch reimplementation of OLMo-core's ``TransformerConfig.olmo3_190M``.

``reference.py`` is the Olmo-Hybrid recipe applied to the same scale, and it is
the floor the agent starts from. The agent will need to solve the problem of
how much further past a competent hybrid it can push val_bpb".
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# --------------------------------------------------------------------------- #
# olmo3_190M's shape and hyper-parameters. Every constant below is upstream's.
# --------------------------------------------------------------------------- #
N_LAYER = 12
N_HEAD = 12
N_EMBD = 768
HEAD_DIM = N_EMBD // N_HEAD
HIDDEN_SIZE = 3072
ROPE_THETA = 500_000.0
NORM_EPS = 1e-6
SWA_PATTERN = (4096, 4096, 4096, -1)
FORCE_FULL_FIRST = False
FORCE_FULL_LAST = True
BLOCK_SIZE = 8192


def window_size_for_layer(layer_idx: int, n_layers: int) -> int:
    """Port of ``SlidingWindowAttentionConfig._get_window_size``. -1 == full."""
    if FORCE_FULL_FIRST and layer_idx == 0:
        return -1
    if FORCE_FULL_LAST and layer_idx == (n_layers - 1):
        return -1
    eff = layer_idx - 1 if FORCE_FULL_FIRST else layer_idx
    return SWA_PATTERN[eff % len(SWA_PATTERN)]


LAYER_WINDOWS = tuple(window_size_for_layer(i, N_LAYER) for i in range(N_LAYER))


class _RMSNorm(nn.Module):
    """LayerNormType.rms with bias=False, eps=1e-6. Computed in fp32."""

    def __init__(self, d: int, eps: float = NORM_EPS):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        dt = x.dtype
        xf = x.float()
        n = xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + self.eps)
        return n.to(dt) * self.weight


# --------------------------------------------------------------------------- #
# Windowed-attention kernel path: FlexAttention, CUDA-only.
# --------------------------------------------------------------------------- #
_FLEX_BLOCK_MASKS: dict = {}
_FLEX_FN = None


def _windowed_attention(q, k, v, window: int) -> torch.Tensor:
    global _FLEX_FN
    if not q.is_cuda:
        raise RuntimeError(
            "baseline_model requires a CUDA device: sliding-window layers run "
            "only through FlexAttention's compiled kernel (no CPU fallback)"
        )
    from torch.nn.attention.flex_attention import (
        create_block_mask,
        flex_attention,
    )

    if _FLEX_FN is None:
        _FLEX_FN = torch.compile(flex_attention, dynamic=False)

    if torch.is_autocast_enabled("cuda"):
        dt = torch.get_autocast_dtype("cuda")
        q, k, v = q.to(dt), k.to(dt), v.to(dt)
    T = q.shape[2]
    key = (T, window, str(q.device))
    bm = _FLEX_BLOCK_MASKS.get(key)
    if bm is None:
        def mask_mod(b, h, qi, ki):
            return (ki <= qi) & (ki > qi - window)

        bm = create_block_mask(mask_mod, None, None, T, T, device=str(q.device))
        _FLEX_BLOCK_MASKS[key] = bm
    return _FLEX_FN(q, k, v, block_mask=bm)


def _rope(x, theta: float = ROPE_THETA):
    """Rotary position embedding over the head dim, computed in fp32.

    theta=500_000 (upstream ``rope_theta``), and ``rope_full_precision=True``
    upstream, hence the fp32 angle computation before casting back.
    """
    _, _, T, D = x.shape
    half = D // 2
    freq = theta ** (-torch.arange(0, half, device=x.device, dtype=torch.float32) / half)
    ang = torch.arange(T, device=x.device, dtype=torch.float32)[:, None] * freq[None, :]
    cos, sin = ang.cos()[None, None], ang.sin()[None, None]
    x1, x2 = x[..., :half].float(), x[..., half:].float()
    return torch.cat([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1).to(x.dtype)


class _Attention(nn.Module):
    """olmo_core AttentionConfig: bias=False, qk_norm=RMSNorm, RoPE, optional SWA."""

    def __init__(self, n_embd: int, n_head: int, window: int):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head, self.n_embd = n_head, n_embd
        self.head_dim = n_embd // n_head
        self.window = window  # -1 == full causal attention
        self.w_q = nn.Linear(n_embd, n_embd, bias=False)
        self.w_k = nn.Linear(n_embd, n_embd, bias=False)
        self.w_v = nn.Linear(n_embd, n_embd, bias=False)
        self.w_out = nn.Linear(n_embd, n_embd, bias=False)
        self.q_norm = _RMSNorm(n_embd)
        self.k_norm = _RMSNorm(n_embd)

    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.w_q(x), self.w_k(x), self.w_v(x)
        q, k = self.q_norm(q), self.k_norm(k)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        q, k = _rope(q), _rope(k)

        if self.window == -1:
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            y = _windowed_attention(q, k, v, self.window)
        return self.w_out(y.transpose(1, 2).contiguous().view(B, T, C))


class _FeedForward(nn.Module):
    """SwiGLU, hidden_size=3072, bias=False (olmo_core FeedForwardConfig)."""

    def __init__(self, n_embd: int, hidden: int = HIDDEN_SIZE):
        super().__init__()
        self.w1 = nn.Linear(n_embd, hidden, bias=False)   # gate
        self.w3 = nn.Linear(n_embd, hidden, bias=False)   # up
        self.w2 = nn.Linear(hidden, n_embd, bias=False)   # down

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class _ReorderedNormBlock(nn.Module):
    """TransformerBlockType.reordered_norm -- norm after the residual branch."""

    def __init__(self, n_embd: int, n_head: int, window: int):
        super().__init__()
        self.attention = _Attention(n_embd, n_head, window)
        self.attention_norm = _RMSNorm(n_embd)
        self.feed_forward = _FeedForward(n_embd)
        self.feed_forward_norm = _RMSNorm(n_embd)

    def forward(self, x):
        h = x + self.attention_norm(self.attention(x))
        return h + self.feed_forward_norm(self.feed_forward(h))


class NanoSLM(nn.Module):
    def __init__(self, config):
        super().__init__()
        if not torch.cuda.is_available():
            raise RuntimeError(
                "baseline_model requires a CUDA device: sliding-window layers "
                "run only through FlexAttention's compiled kernel (no CPU "
                "fallback)"
            )
        self.block_size = config.block_size
        self.wte = nn.Embedding(config.vocab_size, N_EMBD)
        self.blocks = nn.ModuleList(
            [_ReorderedNormBlock(N_EMBD, N_HEAD, w) for w in LAYER_WINDOWS]
        )

        self.norm_f = _RMSNorm(N_EMBD)
        self.lm_head = nn.Linear(N_EMBD, config.vocab_size, bias=False)
        self.apply(self._init_weights)
        for name, p in self.named_parameters():
            if name.endswith("w_out.weight") or name.endswith("w2.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * N_LAYER))
        self.lm_head.weight = self.wte.weight  # weight tying

    @staticmethod
    def _init_weights(module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx):
        x = self.wte(idx)
        for block in self.blocks:
            x = block(x)
        x = self.norm_f(x)
        return self.lm_head(x)  # logits [B, T, vocab_size]


def build_model(config) -> NanoSLM:
    return NanoSLM(config)