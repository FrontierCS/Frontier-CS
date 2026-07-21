"""Locked baseline architecture (hidden; the score-0 reference point).

A plain-PyTorch reimplementation of OLMo-core's ``TransformerConfig.olmo3_190M``,
faithful in every respect EXCEPT that the word embeddings are TIED (see
"ON THE PARAMETER COUNT" below). Upstream unties them; this benchmark ties BOTH
arms (this baseline and ``reference.py``) instead, as a deliberate choice so the
only architectural difference between them is the sequence mixer, not the
output-head param budget. Tying is NOT forced by the ``param_cap`` (400M -- the
untied 267.3M model would fit); it is a comparability choice, and the single
deliberate deviation from upstream.

Implements the exact interface the agent must also honor: ``build_model(config)``
/ ``NanoSLM(config)`` returning a module whose ``forward(idx)`` yields logits
``[B, T, vocab_size]``.

WHAT olmo3_190M ACTUALLY IS (verified against upstream, not reconstructed)
-------------------------------------------------------------------------
``olmo3_190M`` == ``olmo2_190M`` + sliding window + flash_2, and ``olmo2_190M``
is ``llama_like(...)`` with::

    d_model=768, n_layers=12, n_heads=12          -> head_dim 64
    hidden_size_multiplier=1.5
    block_name=TransformerBlockType.reordered_norm
    qk_norm=True
    rope_theta=500_000
    layer_norm_eps=1e-6

``llama_like`` then fixes the rest::

    hidden_size = int(8 * d_model / 3)        # 2048
    hidden_size = int(1.5 * hidden_size)      # 3072
    hidden_size = ensure_multiple_of(., 256)  # 3072
    bias        = False everywhere
    layer_norm  = LayerNormType.rms -> RMSNorm (NOT LayerNorm)

and ``olmo3_190M`` adds::

    SlidingWindowAttentionConfig(pattern=[4096, 4096, 4096, -1],
                                 force_full_attention_on_first_layer=False,
                                 force_full_attention_on_last_layer=True)

THE reordered_norm BLOCK IS NOT PRE-NORM. From upstream ``block.py``::

    h = x + attention_norm(attention(x))
    out = h + feed_forward_norm(feed_forward(h))

The norm is applied to the residual branch's OUTPUT, not to its input. An
earlier revision of this file was a nanoGPT-style pre-norm block with only the
dimensions swapped -- LayerNorm, GELU 4x MLP, biases everywhere, no qk_norm, no
sliding window -- which measured 239,083,008 params and was not olmo3_190M in
any respect other than d/L/H. That is retracted.

ON THE PARAMETER COUNT -- READ THIS BEFORE "FIXING" IT
------------------------------------------------------
Upstream leaves ``tie_word_embeddings`` at its dataclass default of False, so a
faithful olmo3_190M carries TWO vocab-sized matrices and totals **267,310,848**
trainable params at vocab 100278. That fits comfortably under this task's
``param_cap`` of 400,000,000, so the tie is NOT a legality workaround. This
baseline (and ``reference.py``) TIE the embeddings so ``lm_head`` shares
``wte``'s weight, one 77,013,504-param table is removed, and the total drops to::

    12 blocks (113,283,072) + ONE shared embedding table (77,013,504)
        + final norm (768) = 190,297,344

which is the "190M" the model's name refers to. Tying BOTH arms keeps them
differing only in the sequence mixer; the shared table is still ~40% of all
params -- at the 190M shape with a 100278-id vocabulary the embedding dominates;
at 7B the same table is ~11% and near-negligible.

WHY THE BASELINE IS NOT A HYBRID
--------------------------------
``reference.py`` is the Olmo-Hybrid recipe applied to this exact model, and it
is the floor the agent starts from. For that reference to be a meaningful floor
it has to beat something, so the score-0 point is the pure-attention model it
improves on. The scored question is therefore "how much further past a
competent hybrid can you push val_bpb".
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
N_EMBD = 768                  # head_dim = 768 / 12 = 64
HEAD_DIM = N_EMBD // N_HEAD

# int(8*768/3) = 2048 -> int(1.5*2048) = 3072 -> ensure_multiple_of(3072, 256)
HIDDEN_SIZE = 3072

ROPE_THETA = 500_000.0
NORM_EPS = 1e-6

# SlidingWindowAttentionConfig(pattern=[4096,4096,4096,-1],
#                              force_full_attention_on_first_layer=False,
#                              force_full_attention_on_last_layer=True)
SWA_PATTERN = (4096, 4096, 4096, -1)
FORCE_FULL_FIRST = False
FORCE_FULL_LAST = True

# TRAINING CONTEXT OF THE LOCKED ARM, declared through the same module-level
# ``BLOCK_SIZE`` protocol a submission uses (runner.resolve_train_block_size).
#
# Stated EXPLICITLY rather than inheriting the task's ``block_size``: that field
# (8192 in the task config) is now only the submission-facing DEFAULT, and the
# score-0 reference point must not silently move if it is ever retuned. It also
# has to equal ``eval_block_size`` (also 8192) for the cached baseline to remain
# a valid comparison partner for submissions that train shorter -- the baseline
# never trades context for steps, so the trade a submission makes is measured
# against a fixed point.
BLOCK_SIZE = 8192


def window_size_for_layer(layer_idx: int, n_layers: int) -> int:
    """Port of ``SlidingWindowAttentionConfig._get_window_size``. -1 == full.

    Note the ``force_full_attention_on_first_layer`` branch also SHIFTS the
    pattern index (upstream applies the pattern starting from the second layer
    in that case). olmo3 sets it False, so there is no shift here -- but the
    shift is reproduced anyway so the function is a faithful port.
    """
    if FORCE_FULL_FIRST and layer_idx == 0:
        return -1
    if FORCE_FULL_LAST and layer_idx == (n_layers - 1):
        return -1
    eff = layer_idx - 1 if FORCE_FULL_FIRST else layer_idx
    return SWA_PATTERN[eff % len(SWA_PATTERN)]


# For N_LAYER=12 this yields full attention at layers 3, 7, 11 and a 4096-wide
# window everywhere else -- the 9:3 split the reference's 3:1 GDN:attention
# ratio comes from. It is olmo3's own pattern, not an arbitrary choice.
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
# Sliding-window mask cache.
#
# torch's SDPA has no native window flag, so a banded causal mask is built and
# handed to `attn_mask`. It is cached per (T, window, device): one bool mask at
# T=8192 is 64 MiB, so rebuilding it 9x per forward would be ruinous, and all
# nine windowed layers share the same window (4096) hence the same mask.
#
# KERNEL CAVEAT, stated plainly: passing an explicit `attn_mask` disqualifies
# SDPA's fused flash kernel and falls back to the memory-efficient backend,
# whereas upstream uses flash_2's native `window_size=(4095, 0)`. The windowed
# layers are therefore SLOWER here than upstream would be, despite doing fewer
# FLOPs. At ctx 8192 a 4096 window removes only ~25% of attention FLOPs anyway
# (full causal already averages T/2 = 4096 keys per query), so the window is a
# faithfulness feature here, not a speed feature.
# --------------------------------------------------------------------------- #
_MASK_CACHE: dict = {}


def _sliding_causal_mask(T: int, window: int, device) -> torch.Tensor:
    """Bool mask [T, T], True == attend. Keys in [i-window+1, i] inclusive.

    Matches upstream's flash window_size=(window-1, 0), documented there as
    "window is [i - window_size[0], i + window_size[1]] inclusive".
    """
    key = (T, window, str(device))
    m = _MASK_CACHE.get(key)
    if m is None:
        i = torch.arange(T, device=device)
        q, k = i[:, None], i[None, :]
        m = (k <= q) & (k > q - window)
        _MASK_CACHE[key] = m
    return m


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
    """olmo_core AttentionConfig: bias=False, qk_norm=RMSNorm, RoPE, optional SWA.

    qk_norm is applied over the FULL n_heads*head_dim projection, BEFORE the
    head reshape. That is upstream's behaviour when ``use_head_qk_norm`` is
    False, which is the olmo3_190M default (``llama_like`` only forwards
    ``use_head_qk_norm`` when explicitly asked, and olmo2_190M never asks). It
    is NOT a per-head norm -- q_norm/k_norm are 768-wide, not 64-wide.
    """

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
            mask = _sliding_causal_mask(T, self.window, x.device)
            y = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
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
    """TransformerBlockType.reordered_norm -- norm AFTER the residual branch."""

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
        self.block_size = config.block_size
        self.wte = nn.Embedding(config.vocab_size, N_EMBD)
        self.blocks = nn.ModuleList(
            [_ReorderedNormBlock(N_EMBD, N_HEAD, w) for w in LAYER_WINDOWS]
        )
        # LMHeadConfig(layer_norm=rms, bias=False). Embeddings are TIED: the
        # lm_head reuses wte's weight (a comparability choice so both arms differ
        # only in the mixer -- see the module docstring; NOT forced by param_cap).
        # The tie is set AFTER init so the shared tensor carries wte's init.
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