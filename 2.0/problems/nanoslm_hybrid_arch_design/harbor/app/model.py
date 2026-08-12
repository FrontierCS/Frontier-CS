"""Reference solution for nanoslm_hybrid_arch_design -- a 3:1 GDN-to-attention hybrid built on the 190M olmo3_190M shape (254M params).

This is the starting point, not the ceiling. The locked baseline is a faithful
pure-attention ``olmo3_190M``; this file replaces most of its attention layers
with Gated DeltaNet (GDN) linear-recurrent layers.

The 3:1 ratio
-------------
It is not an arbitrary choice. ``olmo3_190M`` already carries::

    SlidingWindowAttentionConfig(pattern=[4096, 4096, 4096, -1],
                                 force_full_attention_on_first_layer=False,
                                 force_full_attention_on_last_layer=True)

so 9 of its 12 layers are sliding-window and 3 (layers 3, 7, 11) are full
attention. This reference replaces each sliding-window layer with a GDN layer and
keeps the full-attention layers::

    block_pattern = ["gdn", "gdn", "gdn", "attn"]

The three sliding-window layers of each 4-layer group become GDN; the
full-attention layer of each group survives untouched. The 3:1 ratio comes from
the base model's own sliding-window pattern. Note the consequence: the hybrid has
No sliding window left anywhere -- every surviving attention layer sat at a
``-1`` position.

No parameter matching
---------------------
A GDN mixer is larger than an attention mixer. This reference does not shrink the
hybrid to match the baseline's parameter count: it keeps the same d=768, h=12,
l=12 as the baseline and lets the hybrid run at its natural (larger) size. With
Tied embeddings::

    baseline   190,354,176   (12 attention layers)
    hybrid     254,430,936   (9 GDN + 3 attention layers)   +33.7% total

(Totals at the padded vocab 100352 -- dolma2's 100278 real ids plus 74 unused
rows on the tied table, the Olmo 3 padding convention.)

The hybrid is bigger -- the GDN mixer's wide recurrent state (head dim
ceil_128(0.75*d/h) = 128) costs params -- but well under the 400M ``param_cap``.
The hard cap -- not an artificial per-arm match -- is what bounds capacity, so
the scored question is whether the mixer choice pays off on quality within that
budget.

``hidden_size`` stays 3072 (the SwiGLU width for d_model 768), same as baseline.

Everything else is identical to the baseline -- RMSNorm eps 1e-6, SwiGLU 3072,
reordered_norm blocks, qk_norm, RoPE theta 500_000, tied embeddings (the baseline
ties, so this arm ties too for comparability) -- so the only architectural
difference is the sequence mixer in those nine layers.

Your task: Push val_bpb further
-------------------------------
This 3:1 GDN hybrid is one point in a large design space. Open questions it does
Not settle, each worth real bpb:

  * The linear-to-attention ratio. 3:1 (GDN:attention) is inherited from the base model's sliding-window pattern,
    which was chosen for a sliding window, not for a linear RNN. 5:1 and 7:1 buy
    more steps but give up more global context.
  * Layer placement. Every 4th, or clustered (early layer for global context in, late
    layer for read-out)? Same cost, different models.
  * State size. ``expand_v`` and ``num_v_heads`` set the recurrent state, the
    main capacity knob of a linear RNN -- unlike a KV cache it does not grow
    with sequence length, so capacity is cheap at 8192.
  * The mixer itself. GDN is one choice; GLA, RetNet and Mamba2-style mixers are
    all expressible in the same chunkwise matmul form.
  * Non-uniformity. Nothing requires every GDN layer to be identical, or the
    attention layers to be full-width.
  * The rest of the block. Norm placement, gating, MLP ratio, head count,
    embedding tying -- all still on the table, and all interact with the above.
  * The training context. Declare a module-level ``BLOCK_SIZE`` int (a power of
    two in [256, 8192]) to train at a shorter context than the default 8192.
    Shorter steps are cheaper, so you complete more of them in the fixed
    wall-clock budget -- but **evaluation is always at 8192**, so the model must
    extrapolate to positions well beyond anything it trained on. How well it
    does that is mostly a property of the position encoding (plain RoPE degrades
    sharply; NTK-aware/YaRN scaling and ALiBi hold up far better), which is a
    different question from mixer efficiency. This file declares no BLOCK_SIZE
    and therefore trains at 8192. Anything sized off ``config.block_size`` must
    still run at ``config.eval_block_size``.

Locked and not yours to change: optimizer, data, tokenizer, the evaluation
context, and the wall-clock budget. Interface: ``build_model(config)`` /
``NanoSLM(config)`` returning ``forward(idx) -> logits [B, T, vocab_size]``.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# --------------------------------------------------------------------------- #
# Architectural Details
# --------------------------------------------------------------------------- #
# Attention hyperparameters
REMOVE_HEADS = 0
N_LAYER = 12
N_HEAD = 12 - REMOVE_HEADS          # 12
HEAD_DIM = 64
N_EMBD = 768 - REMOVE_HEADS * HEAD_DIM   # 768
assert N_EMBD // N_HEAD == HEAD_DIM, "head_dim must be preserved"

HIDDEN_SIZE = 3072                  # SwiGLU width, same as baseline

ROPE_THETA = 500_000.0
NORM_EPS = 1e-6

# GDN hyperparameters
_gdn_raw = int(0.75 * N_EMBD / N_HEAD)
GDN_HEAD_DIM = ((_gdn_raw + 127) // 128) * 128
GDN_EXPAND_V = 2.0
GDN_ALLOW_NEG_EIGVAL = True
GDN_HEAD_V_DIM = int(GDN_HEAD_DIM * GDN_EXPAND_V)      # 256
GDN_KEY_DIM = N_HEAD * GDN_HEAD_DIM                    # 1536
GDN_VALUE_DIM = N_HEAD * GDN_HEAD_V_DIM                # 3072
GDN_CONV_SIZE = 4

PATTERN = ("gdn", "gdn", "gdn", "attn")
assert N_LAYER % len(PATTERN) == 0


class _RMSNorm(nn.Module):
    def __init__(self, d: int, eps: float = NORM_EPS):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        dt = x.dtype
        xf = x.float()
        n = xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + self.eps)
        return n.to(dt) * self.weight


def _rope(x, theta: float = ROPE_THETA):
    _, _, T, D = x.shape
    half = D // 2
    freq = theta ** (-torch.arange(0, half, device=x.device, dtype=torch.float32) / half)
    ang = torch.arange(T, device=x.device, dtype=torch.float32)[:, None] * freq[None, :]
    cos, sin = ang.cos()[None, None], ang.sin()[None, None]
    x1, x2 = x[..., :half].float(), x[..., half:].float()
    return torch.cat([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1).to(x.dtype)


class _Attention(nn.Module):
    """Identical to the baseline's attention, always full causal."""

    def __init__(self, n_embd: int, n_head: int):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head, self.n_embd = n_head, n_embd
        self.head_dim = n_embd // n_head
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
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.w_out(y.transpose(1, 2).contiguous().view(B, T, C))


def _make_gdn():
    """fla's fused GatedDeltaNet. CUDA required."""
    if not torch.cuda.is_available():
        raise RuntimeError(
            "reference hybrid requires a CUDA device: the GDN layers run only "
            "through fla's fused Triton kernels, and there is deliberately no "
            "CPU fallback"
        )

    from fla.layers import GatedDeltaNet
    return GatedDeltaNet(
        hidden_size=N_EMBD,
        num_heads=N_HEAD,
        head_dim=GDN_HEAD_DIM,
        expand_v=GDN_EXPAND_V,
        allow_neg_eigval=GDN_ALLOW_NEG_EIGVAL,
        use_gate=True,
        use_short_conv=True,
    )


class _GDNLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.impl = _make_gdn()

    def forward(self, x):
        out = self.impl(x)
        # fla layers return (hidden_states, attentions, past_kv) -- keep only
        # the hidden states.
        return out[0] if isinstance(out, tuple) else out


class _FeedForward(nn.Module):
    """SwiGLU, hidden 3072, bias=False -- unchanged from the baseline."""

    def __init__(self, n_embd: int, hidden: int = HIDDEN_SIZE):
        super().__init__()
        self.w1 = nn.Linear(n_embd, hidden, bias=False)
        self.w3 = nn.Linear(n_embd, hidden, bias=False)
        self.w2 = nn.Linear(hidden, n_embd, bias=False)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class _ReorderedNormBlock(nn.Module):
    """Upstream builds the GDN block as ``attn_block.replace(sequence_mixer=...)``
    -- same reordered_norm structure, same norms, only the mixer swapped."""

    def __init__(self, n_embd: int, n_head: int, kind: str):
        super().__init__()
        self.attention = _Attention(n_embd, n_head) if kind == "attn" else _GDNLayer()
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
        kinds = [PATTERN[i % len(PATTERN)] for i in range(N_LAYER)]
        self.blocks = nn.ModuleList([_ReorderedNormBlock(N_EMBD, N_HEAD, k) for k in kinds])
        self.norm_f = _RMSNorm(N_EMBD)

        self.lm_head = nn.Linear(N_EMBD, config.vocab_size, bias=False)
        self.apply(self._init)

        for name, p in self.named_parameters():
            if name.endswith(("w_out.weight", "w2.weight", "o_proj.weight")):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * N_LAYER))
        self.lm_head.weight = self.wte.weight  # weight tying

    @staticmethod
    def _init(m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def forward(self, idx):
        x = self.wte(idx)
        for block in self.blocks:
            x = block(x)
        x = self.norm_f(x)
        return self.lm_head(x)  # logits [B, T, vocab_size]


def build_model(config) -> NanoSLM:
    return NanoSLM(config)


def analytic_n_params(vocab_size: int) -> int:
    """Analytic total, derived from the spec rather than from a measurement."""
    d, H, hid = N_EMBD, N_HEAD, HIDDEN_SIZE
    block_norms = 2 * d
    ffn = 3 * d * hid
    attn_mix = 4 * d * d + 2 * d                      # projections + q/k norms
    gdn_mix = (
        2 * d * GDN_KEY_DIM                           # q_proj, k_proj
        + 2 * d * GDN_VALUE_DIM                       # v_proj, g_proj
        + 2 * d * H                                   # a_proj, b_proj
        + GDN_VALUE_DIM * d                           # o_proj
        + 2 * H                                       # A_log, dt_bias
        + GDN_CONV_SIZE * (2 * GDN_KEY_DIM + GDN_VALUE_DIM)   # short convs
        + GDN_HEAD_V_DIM                              # o_norm
    )
    n_attn = sum(1 for i in range(N_LAYER) if PATTERN[i % len(PATTERN)] == "attn")
    n_gdn = N_LAYER - n_attn
    non_emb = n_attn * (attn_mix + block_norms + ffn) + n_gdn * (gdn_mix + block_norms + ffn) + d

    return non_emb + vocab_size * d


def _self_check(vocab_size: int = 100352) -> int:
    # A minimal stand-in for the harness-provided config object
    class _Cfg:
        def __init__(self, vocab_size: int, block_size: int,
                     eval_block_size: int = 8192):
            self.vocab_size = vocab_size
            self.block_size = block_size
            self.eval_block_size = eval_block_size

    m = NanoSLM(_Cfg(vocab_size, 8192))
    got = sum(p.numel() for p in m.parameters() if p.requires_grad)
    want = analytic_n_params(vocab_size)
    assert got == want, f"param mismatch: built {got} != analytic {want}"
    return got
