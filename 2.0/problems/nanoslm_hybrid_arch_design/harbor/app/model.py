"""Reference solution for nanoslm_hybrid_arch_design -- the Olmo-Hybrid recipe at 190M.

This is the STARTING POINT, not the ceiling. The locked baseline is a faithful
``olmo3_190M``; this file applies OLMo-core's own hybrid recipe
(``src/scripts/train/OLMo_hybrid/OLMo-hybrid-7B.py``) to it.

WHERE THE 3:1 RATIO ACTUALLY COMES FROM
---------------------------------------
It is NOT an arbitrary choice. ``olmo3_190M`` already carries::

    SlidingWindowAttentionConfig(pattern=[4096, 4096, 4096, -1],
                                 force_full_attention_on_first_layer=False,
                                 force_full_attention_on_last_layer=True)

so 9 of its 12 layers are sliding-window and 3 (layers 3, 7, 11) are full
attention. The paper "replaces sliding window layers with Gated DeltaNet
layers", and upstream's recipe encodes exactly that::

    config.block_pattern = ["gdn", "gdn", "gdn", "attn"]

The three sliding-window layers of each 4-layer group become GDN; the
full-attention layer of each group survives untouched. The 3:1 ratio IS olmo3's
own sliding-window pattern. Note the consequence: the hybrid has NO sliding
window left anywhere -- every surviving attention layer sat at a ``-1`` position.

PARAMETER MATCHING (upstream's REMOVE_HEADS practice)
-----------------------------------------------------
GDN's mixer is larger than an attention mixer, so upstream shrinks the model to
compensate rather than letting the hybrid quietly buy capacity::

    REMOVE_HEADS = 2
    config.d_model -= REMOVE_HEADS * 128      # 4096 -> 3840
    num_heads      -= REMOVE_HEADS            # 32 -> 30
    assert config.d_model / num_heads == 128  # head_dim preserved

At 190M with head_dim 64 the equivalent is ``REMOVE_HEADS = 1``::

    d_model 768 -> 704,  n_heads 12 -> 11,  704 / 11 == 64  (head_dim preserved)

Matching is done on NON-EMBEDDING parameters, which is the quantity upstream
itself feeds to ``Duration.chinchilla_tokens(model_params=...)``. Both arms TIE
their single vocab table, which at this scale is ~40% of all parameters --
including it would drown the mixer difference being matched. Measured
analytically:

    baseline  non-embedding   113,283,840
    hybrid    non-embedding   110,805,734      -2.19%

which is the same tolerance upstream's own 7B pair achieves (+2.84%). One caveat
worth stating: because ``d_model`` shrinks 768 -> 704, the tied table shrinks too
(77.0M -> 70.6M), so the hybrid's TOTAL is 4.7% below the baseline's
(181,401,446 vs 190,297,344) even though its non-embedding count is within 2.2%.

Note also that ``hidden_size`` stays 3072. Upstream mutates ``d_model`` in place
and never recomputes the feed-forward width, so the FFN keeps the width derived
from the ORIGINAL d_model. Reproduced here deliberately.

Everything else is identical to the baseline -- RMSNorm eps 1e-6, SwiGLU 3072,
reordered_norm blocks, qk_norm, RoPE theta 500_000, TIED embeddings (the baseline
ties, so this arm ties too for comparability) -- so the ONLY architectural
difference is the sequence mixer in those nine layers.

YOUR TASK: PUSH val_bpb FURTHER
-------------------------------
Everything above is upstream's recipe, transposed to this scale. The open
questions it does NOT answer, each worth real bpb:

  * THE RATIO. 3:1 is inherited from olmo3's sliding-window pattern, which was
    chosen for a sliding window, not for a linear RNN. 5:1 and 7:1 buy more
    steps but give up more global context.
  * PLACEMENT. Every 4th, or clustered (early layer for global context in, late
    layer for read-out)? Same cost, different models.
  * STATE SIZE. ``expand_v`` and ``num_v_heads`` set the recurrent state, the
    main capacity knob of a linear RNN -- unlike a KV cache it does not grow
    with sequence length, so capacity is cheap at 8192.
  * THE MIXER ITSELF. GDN is one choice; GLA, RetNet and Mamba2-style mixers are
    all expressible in the same chunkwise matmul form.
  * NON-UNIFORMITY. Nothing requires every GDN layer to be identical, or the
    attention layers to be full-width.
  * THE REST OF THE BLOCK. Norm placement, gating, MLP ratio, head count,
    embedding tying -- all still on the table, and all interact with the above.
  * THE TRAINING CONTEXT. Declare a module-level ``BLOCK_SIZE`` int (a power of
    two in [256, 8192]) to train at a shorter context than the default 8192.
    Shorter steps are cheaper, so you complete more of them in the fixed
    wall-clock budget -- but EVALUATION IS ALWAYS AT 8192, so the model must
    extrapolate to positions well beyond anything it trained on. How well it
    does that is mostly a property of the POSITION ENCODING (plain RoPE degrades
    sharply; NTK-aware/YaRN scaling and ALiBi hold up far better), which is a
    different question from mixer efficiency. This file declares no BLOCK_SIZE
    and therefore trains at 8192. Anything sized off ``config.block_size`` must
    still run at ``config.eval_block_size``.

Locked and not yours to change: optimizer, data, tokenizer, the EVALUATION
context (8192), and the wall-clock budget. Interface: ``build_model(config)`` /
``NanoSLM(config)`` returning ``forward(idx) -> logits [B, T, vocab_size]``.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# --------------------------------------------------------------------------- #
# Shape: olmo3_190M with upstream's REMOVE_HEADS compensation applied.
# --------------------------------------------------------------------------- #
REMOVE_HEADS = 1

N_LAYER = 12
N_HEAD = 12 - REMOVE_HEADS          # 11
HEAD_DIM = 64                       # preserved, exactly as upstream asserts
N_EMBD = 768 - REMOVE_HEADS * HEAD_DIM   # 704
assert N_EMBD // N_HEAD == HEAD_DIM, "REMOVE_HEADS must preserve head_dim"

# NOT recomputed from the reduced d_model -- upstream mutates d_model in place
# and leaves the feed-forward width at the value llama_like derived from the
# ORIGINAL 768. Reproduced deliberately.
HIDDEN_SIZE = 3072

ROPE_THETA = 500_000.0
NORM_EPS = 1e-6

# GatedDeltaNetConfig(n_heads=num_heads, head_dim=int(0.75*d_model/num_heads),
#                     allow_neg_eigval=True) with expand_v at its 2.0 default.
GDN_HEAD_DIM = int(0.75 * N_EMBD / N_HEAD)      # 48
GDN_EXPAND_V = 2.0
GDN_HEAD_V_DIM = int(GDN_HEAD_DIM * GDN_EXPAND_V)   # 96
GDN_KEY_DIM = N_HEAD * GDN_HEAD_DIM                 # 528
GDN_VALUE_DIM = N_HEAD * GDN_HEAD_V_DIM             # 1056
GDN_CONV_SIZE = 4

# config.block_pattern = ["gdn", "gdn", "gdn", "attn"] -- the three
# sliding-window layers of each group become GDN, the full-attention layer
# survives. Attention therefore lands at layers 3, 7, 11.
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
    """Identical to the baseline's attention, always FULL causal.

    Full, not windowed, and that is not a simplification: the attention layers
    the hybrid keeps are exactly the ones sitting at the ``-1`` positions of
    olmo3's [4096, 4096, 4096, -1] pattern, so they were already full attention
    before the GDN substitution.

    qk_norm spans the full n_heads*head_dim projection and is applied BEFORE the
    head reshape -- upstream's behaviour when ``use_head_qk_norm`` is False,
    which is the olmo3_190M default.
    """

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


class _ChunkedDeltaNet(nn.Module):
    """CPU-only chunkwise fallback, PARAMETER-IDENTICAL to fla's GatedDeltaNet.

    Exists so the CPU smoke path can build and report the same parameter count
    the CUDA path will. Its module inventory is fla 0.5.1's exactly --
    q/k/v/a/b/g/o projections, three depthwise short convolutions, A_log,
    dt_bias and the gated output norm -- so ``n_params`` is device-independent.

    The recurrence is a chunkwise GATED LINEAR ATTENTION, not the full delta
    rule: it carries the decay and the gates but skips the delta-rule inverse.
    That is a deliberate approximation. It is never scored -- CUDA raises rather
    than falling back here (see ``_make_gdn``) -- and it exists to prove wiring,
    not to reproduce GDN's numerics.
    """

    def __init__(self, chunk: int = 512):
        super().__init__()
        self.chunk = chunk
        d, H = N_EMBD, N_HEAD
        self.q_proj = nn.Linear(d, GDN_KEY_DIM, bias=False)
        self.k_proj = nn.Linear(d, GDN_KEY_DIM, bias=False)
        self.v_proj = nn.Linear(d, GDN_VALUE_DIM, bias=False)
        self.a_proj = nn.Linear(d, H, bias=False)
        self.b_proj = nn.Linear(d, H, bias=False)
        self.g_proj = nn.Linear(d, GDN_VALUE_DIM, bias=False)
        self.o_proj = nn.Linear(GDN_VALUE_DIM, d, bias=False)
        self.A_log = nn.Parameter(torch.zeros(H))
        self.dt_bias = nn.Parameter(torch.zeros(H))
        # ShortConvolution weights: depthwise, (channels, 1, kernel), no bias.
        self.q_conv1d = nn.Parameter(torch.zeros(GDN_KEY_DIM, 1, GDN_CONV_SIZE))
        self.k_conv1d = nn.Parameter(torch.zeros(GDN_KEY_DIM, 1, GDN_CONV_SIZE))
        self.v_conv1d = nn.Parameter(torch.zeros(GDN_VALUE_DIM, 1, GDN_CONV_SIZE))
        self.o_norm = nn.Parameter(torch.ones(GDN_HEAD_V_DIM))

    @staticmethod
    def _short_conv(x, w):
        """Causal depthwise conv over time. x [B, T, C], w [C, 1, K]."""
        C, K = w.shape[0], w.shape[2]
        xt = F.pad(x.transpose(1, 2), (K - 1, 0))
        return F.conv1d(xt, w, groups=C).transpose(1, 2)

    def forward(self, x):
        B, T, _ = x.shape
        H, DK, DV, S = N_HEAD, GDN_HEAD_DIM, GDN_HEAD_V_DIM, self.chunk

        q = F.silu(self._short_conv(self.q_proj(x), self.q_conv1d))
        k = F.silu(self._short_conv(self.k_proj(x), self.k_conv1d))
        v = self._short_conv(self.v_proj(x), self.v_conv1d)

        q = q.view(B, T, H, DK).transpose(1, 2)
        k = k.view(B, T, H, DK).transpose(1, 2)
        v = v.view(B, T, H, DV).transpose(1, 2)

        # Per-head decay in (0, 1): the gate that makes this "gated".
        dt = F.softplus(self.a_proj(x) + self.dt_bias)          # [B, T, H]
        g = torch.exp(-torch.exp(self.A_log) * dt)              # [B, T, H]
        g = g.permute(0, 2, 1).unsqueeze(-1)                    # [B, H, T, 1]
        beta = torch.sigmoid(self.b_proj(x)).permute(0, 2, 1).unsqueeze(-1)
        v = v * beta

        pad = (S - T % S) % S
        if pad:
            q, k, v = (F.pad(t, (0, 0, 0, pad)) for t in (q, k, v))
            g = F.pad(g, (0, 0, 0, pad), value=1.0)
        nC = (T + pad) // S
        rs = lambda t: t.view(B, H, nC, S, -1)  # noqa: E731
        qc, kc, vc, gc = rs(q), rs(k), rs(v), rs(g)

        causal = torch.tril(torch.ones(S, S, device=x.device, dtype=torch.bool))
        intra = (qc @ kc.transpose(-1, -2)).masked_fill(~causal, 0.0) @ vc

        state = torch.zeros(B, H, DK, DV, device=x.device, dtype=x.dtype)
        outs = []
        for c in range(nC):
            outs.append(intra[:, :, c] + qc[:, :, c] @ state)
            decay = gc[:, :, c].prod(dim=2, keepdim=True)
            state = state * decay + kc[:, :, c].transpose(-1, -2) @ (vc[:, :, c] * gc[:, :, c])
        y = torch.stack(outs, dim=2).view(B, H, T + pad, DV)[:, :, :T]

        # Gated RMSNorm over head_v_dim, then merge heads.
        yf = y.float()
        y = (yf * torch.rsqrt(yf.pow(2).mean(-1, keepdim=True) + 1e-5)).to(x.dtype)
        y = y * self.o_norm
        y = y.transpose(1, 2).contiguous().view(B, T, GDN_VALUE_DIM)
        y = y * F.silu(self.g_proj(x))
        return self.o_proj(y)


def _make_gdn():
    """fla's fused GatedDeltaNet on CUDA; chunkwise only on CPU (smoke).

    WHY fla IS REQUIRED HERE, not merely preferred: PyTorch ships a fused kernel
    for softmax attention (SDPA) but none for a linear/recurrent mixer, so a
    hand-written GDN is unfused eager code. Scoring is fixed WALL-CLOCK, so an
    unfused mixer loses on throughput regardless of architectural merit --
    measured at ctx 8192, the chunkwise fallback did 6% of attention's FLOPs and
    still ran 3.5x slower. Both arms must be kernel-matched or the score
    measures kernel quality, not architecture.

    HARD FAILURE ON CUDA, deliberately: a silent fallback here once produced a
    scored-looking run where the reference "lost" 18 steps to 65 purely because
    fla was missing. A missing kernel must raise, not quietly change what is
    being measured.
    """
    if not torch.cuda.is_available():
        return _ChunkedDeltaNet()

    from fla.layers import GatedDeltaNet  # ImportError here is intentional

    # head_dim MUST be passed: fla defaults it to 256, so omitting it builds
    # num_heads*256-wide projections instead of the intended width -- a silent
    # param blowup that trains a much larger model than the baseline.
    return GatedDeltaNet(
        hidden_size=N_EMBD,
        num_heads=N_HEAD,
        head_dim=GDN_HEAD_DIM,
        expand_v=GDN_EXPAND_V,
        use_gate=True,
        use_short_conv=True,
    )


class _GDNLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.impl = _make_gdn()

    def forward(self, x):
        out = self.impl(x)
        # fla layers return (hidden_states, attentions, past_kv); the chunkwise
        # fallback returns a tensor. Normalize so _Block need not care.
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
        # TIED -- the baseline ties its embeddings (a deliberate deviation from
        # upstream's untied default), so the reference ties too and the two arms
        # stay comparable: the ONLY architectural difference between them is the
        # sequence mixer in the GDN layers, not the output-head param budget. The
        # tie is set AFTER init (below) so the shared table carries wte's init.
        self.lm_head = nn.Linear(N_EMBD, config.vocab_size, bias=False)
        self.apply(self._init)
        for name, p in self.named_parameters():
            if name.endswith("w_out.weight") or name.endswith("w2.weight"):
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
    # ONE vocab-sized table: lm_head is TIED to wte (see NanoSLM.__init__).
    return non_emb + vocab_size * d


def _self_check(vocab_size: int = 100278) -> int:
    from harness.model_config import ModelConfig

    m = NanoSLM(ModelConfig(vocab_size=vocab_size, block_size=8192))
    got = sum(p.numel() for p in m.parameters() if p.requires_grad)
    want = analytic_n_params(vocab_size)
    assert got == want, f"param mismatch: built {got} != analytic {want}"
    return got
