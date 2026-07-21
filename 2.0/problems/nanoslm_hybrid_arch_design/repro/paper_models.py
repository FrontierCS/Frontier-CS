"""Paper-faithful 190M ablation models for reproducing Olmo Hybrid Table 5.

These are DELIBERATELY NOT the benchmark's ``baseline_model.py`` / ``reference.py``.
The Table 5 numbers (Transformer 0.950, GDN-3:1 0.891 Base-Easy BPB @ 190M) were
produced by the scaling-ladder ablation models described in arXiv:2604.03444
Section D.3 + Table 22, which differ from the benchmark variants in three ways:

  * NORM PLACEMENT: pre-norm (RMSNorm BEFORE each sub-layer), per D.3
    ("RMSNorm applied before each sub-layer (pre-norm)"). The benchmark's
    baseline_model.py uses reordered_norm (norm AFTER the residual branch).
  * BASELINE ATTENTION: plain full multi-head causal attention. D.3 describes
    no sliding window for the ablation ladder; the benchmark baseline uses a
    9:3 SWA (4096-window) pattern.
  * HYBRID SIZING: the ablation hybrid keeps the SAME d=768, h=12, l=12 as the
    transformer (non-embedding params grow 190M -> 254M). The benchmark's
    reference.py instead param-matches via REMOVE_HEADS=1 (d704, h11).

Shape (Table 22, 190M column): d=768, h=12, l=12, head_dim=64.
MLP: SwiGLU, hidden = round_up_256(1.5 * 8d/3) = 3072 (D.3).
Untied embeddings; RoPE theta 500_000; QK-norm; RMSNorm eps 1e-6.
Vocab: dolma2, 100352 padded (D.3). BPB is vocab-padding-invariant, but we use
100352 to match the paper's embedding shape exactly.

GDN (D.3 + Appendix A.1): head sizing proportional to an attention head --
d_k = 3/4 * head_dim = 48, d_v = 2 * d_k = 96 (expand_v = 2.0), allow_neg_eigval
= True, use_gate = True, use_short_conv = True. fla's GatedDeltaNet is REQUIRED
on CUDA (a hand-written mixer is unfused and would confound any timing); a
chunkwise CPU fallback exists only so param counts / wiring are checkable off-GPU.

Placement (D.3): "every r-th layer is a full transformer block" with r=4 (3:1),
"and we additionally enforce the final layer be an attention layer". For l=12
that is attention at layers 3, 7, 11 (0-indexed), i.e. pattern (gdn,gdn,gdn,attn).
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# --------------------------------------------------------------------------- #
# Shared shape (Table 22, 190M).
# --------------------------------------------------------------------------- #
N_LAYER = 12
N_HEAD = 12
N_EMBD = 768
HEAD_DIM = N_EMBD // N_HEAD          # 64
HIDDEN_SIZE = 3072                   # round_up_256(1.5 * 8*768/3) = 3072
ROPE_THETA = 500_000.0
NORM_EPS = 1e-6

# GDN head sizing (D.3): hGDN = ceil_128(0.75 * d/h), where ceil_128 rounds UP
# to the nearest multiple of 128. For 190M: 0.75 * 768/12 = 48 -> 128. Key dim
# = h * hGDN, value dim = h * 2*hGDN (expand_v = 2). This ceil-to-128 is what
# reference.py omitted (it used 48), and it is why the ablation hybrid is 254M
# non-embed, not ~201M -- the GDN mixer is ~9.5M/layer, not ~3.6M.
def _ceil_mult(x: int, m: int) -> int:
    return ((x + m - 1) // m) * m

GDN_HEAD_DIM = _ceil_mult(int(0.75 * HEAD_DIM), 128)   # ceil_128(48) = 128
GDN_EXPAND_V = 2.0
GDN_HEAD_V_DIM = int(GDN_HEAD_DIM * GDN_EXPAND_V)       # 256
GDN_KEY_DIM = N_HEAD * GDN_HEAD_DIM                     # 1536
GDN_VALUE_DIM = N_HEAD * GDN_HEAD_V_DIM                 # 3072
GDN_CONV_SIZE = 4

# r=4 (3:1) interleave, final layer forced to attention -> attn at 3, 7, 11.
PATTERN = ("gdn", "gdn", "gdn", "attn")
assert N_LAYER % len(PATTERN) == 0


class RMSNorm(nn.Module):
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


class Attention(nn.Module):
    """Full causal MHA with QK-norm (full-width, pre-reshape) + RoPE. No SWA."""

    def __init__(self, n_embd: int = N_EMBD, n_head: int = N_HEAD):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head, self.n_embd = n_head, n_embd
        self.head_dim = n_embd // n_head
        self.w_q = nn.Linear(n_embd, n_embd, bias=False)
        self.w_k = nn.Linear(n_embd, n_embd, bias=False)
        self.w_v = nn.Linear(n_embd, n_embd, bias=False)
        self.w_out = nn.Linear(n_embd, n_embd, bias=False)
        self.q_norm = RMSNorm(n_embd)
        self.k_norm = RMSNorm(n_embd)

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
    """CPU-only chunkwise fallback, param-identical to fla's GatedDeltaNet.

    Numerically approximate (gated linear attention, no delta-rule inverse);
    exists ONLY so param counts / wiring are checkable off-GPU. Never used on
    CUDA -- _make_gdn raises there if fla is missing.
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
        self.q_conv1d = nn.Parameter(torch.zeros(GDN_KEY_DIM, 1, GDN_CONV_SIZE))
        self.k_conv1d = nn.Parameter(torch.zeros(GDN_KEY_DIM, 1, GDN_CONV_SIZE))
        self.v_conv1d = nn.Parameter(torch.zeros(GDN_VALUE_DIM, 1, GDN_CONV_SIZE))
        self.o_norm = nn.Parameter(torch.ones(GDN_HEAD_V_DIM))

    @staticmethod
    def _short_conv(x, w):
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
        dt = F.softplus(self.a_proj(x) + self.dt_bias)
        g = torch.exp(-torch.exp(self.A_log) * dt).permute(0, 2, 1).unsqueeze(-1)
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
        yf = y.float()
        y = (yf * torch.rsqrt(yf.pow(2).mean(-1, keepdim=True) + 1e-5)).to(x.dtype)
        y = y * self.o_norm
        y = y.transpose(1, 2).contiguous().view(B, T, GDN_VALUE_DIM)
        y = y * F.silu(self.g_proj(x))
        return self.o_proj(y)


def _make_gdn():
    if not torch.cuda.is_available():
        return _ChunkedDeltaNet()
    from fla.layers import GatedDeltaNet  # ImportError here is intentional
    return GatedDeltaNet(
        hidden_size=N_EMBD,
        num_heads=N_HEAD,
        head_dim=GDN_HEAD_DIM,
        expand_v=GDN_EXPAND_V,
        use_gate=True,
        use_short_conv=True,
        allow_neg_eigval=True,
    )


class GDNLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.impl = _make_gdn()

    def forward(self, x):
        out = self.impl(x)
        return out[0] if isinstance(out, tuple) else out


class FeedForward(nn.Module):
    """SwiGLU, hidden 3072, bias=False."""

    def __init__(self, n_embd: int = N_EMBD, hidden: int = HIDDEN_SIZE):
        super().__init__()
        self.w1 = nn.Linear(n_embd, hidden, bias=False)
        self.w3 = nn.Linear(n_embd, hidden, bias=False)
        self.w2 = nn.Linear(hidden, n_embd, bias=False)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class PreNormBlock(nn.Module):
    """Pre-norm (D.3): norm BEFORE each sub-layer, residual add after."""

    def __init__(self, kind: str):
        super().__init__()
        self.mixer = Attention() if kind == "attn" else GDNLayer()
        self.mixer_norm = RMSNorm(N_EMBD)
        self.ffn = FeedForward()
        self.ffn_norm = RMSNorm(N_EMBD)

    def forward(self, x):
        x = x + self.mixer(self.mixer_norm(x))
        return x + self.ffn(self.ffn_norm(x))


class PaperModel(nn.Module):
    """Paper-faithful ablation model. ``hybrid=False`` -> pure transformer."""

    def __init__(self, config, hybrid: bool):
        super().__init__()
        self.block_size = config.block_size
        self.wte = nn.Embedding(config.vocab_size, N_EMBD)
        if hybrid:
            kinds = [PATTERN[i % len(PATTERN)] for i in range(N_LAYER)]
        else:
            kinds = ["attn"] * N_LAYER
        self.blocks = nn.ModuleList([PreNormBlock(k) for k in kinds])
        self.norm_f = RMSNorm(N_EMBD)
        self.lm_head = nn.Linear(N_EMBD, config.vocab_size, bias=False)  # untied
        self.apply(self._init)
        for name, p in self.named_parameters():
            if name.endswith("w_out.weight") or name.endswith("w2.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * N_LAYER))

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
        return self.lm_head(x)


def build_transformer(config):
    return PaperModel(config, hybrid=False)


def build_hybrid(config):
    return PaperModel(config, hybrid=True)


# --------------------------------------------------------------------------- #
# Analytic param counts (Table 22 convention: "non-embedding" = blocks + LM
# head, i.e. everything except the INPUT embedding table). At 190M this should
# reproduce Transformer 190 and GDN-3:1 254 (millions).
# --------------------------------------------------------------------------- #
def _attn_params():
    d = N_EMBD
    return 4 * d * d + 2 * d          # q/k/v/out + q/k norm


def _gdn_params():
    d, H = N_EMBD, N_HEAD
    return (
        2 * d * GDN_KEY_DIM            # q_proj, k_proj
        + 2 * d * GDN_VALUE_DIM        # v_proj, g_proj
        + 2 * d * H                    # a_proj, b_proj
        + GDN_VALUE_DIM * d            # o_proj
        + 2 * H                        # A_log, dt_bias
        + GDN_CONV_SIZE * (2 * GDN_KEY_DIM + GDN_VALUE_DIM)  # short convs
        + GDN_HEAD_V_DIM               # o_norm
    )


def analytic_non_embed(hybrid: bool, vocab_size: int) -> int:
    d = N_EMBD
    block_norms = 2 * d
    ffn = 3 * d * HIDDEN_SIZE
    n_attn = sum(1 for i in range(N_LAYER) if PATTERN[i % len(PATTERN)] == "attn") if hybrid else N_LAYER
    n_gdn = N_LAYER - n_attn
    blocks = n_attn * (_attn_params() + block_norms + ffn) + n_gdn * (_gdn_params() + block_norms + ffn)
    lm_head = vocab_size * d          # counted as non-embedding (Table 22 convention)
    return blocks + d + lm_head       # + final norm


if __name__ == "__main__":
    # Local self-check (CPU): param counts vs Table 22 (190 / 254 million).
    class _Cfg:
        vocab_size = 100352
        block_size = 256
        eval_block_size = 256

    for hybrid, want in ((False, 190), (True, 254)):
        m = PaperModel(_Cfg(), hybrid=hybrid)
        total = sum(p.numel() for p in m.parameters() if p.requires_grad)
        non_emb_built = total - m.wte.weight.numel()
        non_emb_analytic = analytic_non_embed(hybrid, _Cfg.vocab_size)
        assert non_emb_built == non_emb_analytic, (hybrid, non_emb_built, non_emb_analytic)
        name = "hybrid GDN-3:1" if hybrid else "transformer"
        print(f"{name:16s} non-embed(Table22 conv)={non_emb_built/1e6:6.1f}M "
              f"(want ~{want}M)  total={total/1e6:6.1f}M")
        # tiny forward
        idx = torch.randint(0, _Cfg.vocab_size, (2, 16))
        out = m(idx)
        assert out.shape == (2, 16, _Cfg.vocab_size), out.shape
    print("forward + param-count self-check OK")
