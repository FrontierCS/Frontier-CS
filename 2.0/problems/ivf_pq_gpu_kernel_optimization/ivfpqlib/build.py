"""Naive IVF-PQ index builder (pure torch, deterministic, CPU-OK).

Builds an :class:`~ivfpqlib.index.IvfPqIndex`: a coarse k-means quantizer over
``nlist`` cells + ``m`` product-quantization sub-codebooks, then encodes every
database row to an ``(M, m)`` uint8 code in CSR cell-contiguous layout. This is
the **frozen** index construction (it is not the timed operation); search is
what you optimize. ADC contract: a candidate with codes ``code`` probing list
``c`` scores ``sum_s || rq_s - codebook[s, code[s]] ||^2`` where the residual
query ``rq = q - centroid[c]`` (``by_residual``) or ``q`` otherwise.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import torch

from ivfpqlib.index import IvfPqIndex

def _pad_features(x: torch.Tensor, Dp: int) -> torch.Tensor:
    """Zero-pad the trailing feature dim to ``Dp`` (no-op when already wide)."""
    D = x.shape[-1]
    if D >= Dp:
        return x
    pad = torch.zeros((*x.shape[:-1], Dp - D), device=x.device, dtype=x.dtype)
    return torch.cat([x, pad], dim=-1)


def _pq_dims(D: int, m: int) -> Tuple[int, int, int]:
    """Resolve ``(m, dsub, Dp)`` for a ``D``-dim input split into ``m`` codes.

    ``dsub = ceil(D / m)`` and ``Dp = m * dsub`` (the zero-padded working
    width). ``dsub`` is bumped until ``Dp >= 16`` so the coarse-quantizer
    kernels (which use ``tl.dot``) always have a contraction dim >= 16;
    the zero columns never change squared-L2 distances.
    """
    m = int(m)
    if m < 1:
        raise ValueError(f"m (number of sub-quantizers) must be >= 1 (got {m})")
    if m > D:
        # More sub-quantizers than dims: clamp so each sub-vector has >= 1 dim.
        m = int(D)
    dsub = int(math.ceil(D / m))
    while m * dsub < 16:
        dsub += 1
    return m, dsub, m * dsub


# ── tiny CPU-OK building blocks ────────────────────────────────────────────
def _lloyd_kmeans(
    sample: torch.Tensor, k: int, *, niter: int, seed: int
) -> torch.Tensor:
    """Tiny Lloyd k-means returning ``(k, D)`` centroids (fp32 math)."""
    n = sample.shape[0]
    if n < k:
        raise ValueError(
            f"k-means needs at least k={k} training rows (got {n}); "
            "increase train_size / pq_train_size or lower nlist / m."
        )
    g = torch.Generator(device="cpu").manual_seed(seed)
    perm = torch.randperm(n, generator=g)[:k]
    centroids = sample[perm.to(sample.device)].to(torch.float32).clone()
    s = sample.to(torch.float32)
    for _ in range(max(1, niter)):
        d2 = torch.cdist(s, centroids) ** 2          # (n, k)
        assign = d2.argmin(dim=1)                    # (n,)
        new = centroids.clone()
        for c in range(k):
            mask = assign == c
            if bool(mask.any()):
                new[c] = s[mask].mean(dim=0)
        shift = (new - centroids).norm(dim=-1).max()
        centroids = new
        if float(shift) == 0.0:
            break
    return centroids.to(torch.float32)


def _assign_chunked(
    Xp: torch.Tensor, centroids: torch.Tensor, chunk: int = 8192
) -> torch.Tensor:
    """Nearest-centroid id per row (squared-L2), chunked to bound memory."""
    out = torch.empty(Xp.shape[0], dtype=torch.int64, device=Xp.device)
    cf = centroids.to(torch.float32)
    for lo in range(0, Xp.shape[0], chunk):
        hi = min(lo + chunk, Xp.shape[0])
        d2 = torch.cdist(Xp[lo:hi].to(torch.float32), cf) ** 2
        out[lo:hi] = d2.argmin(dim=1)
    return out


def _train_pq_codebooks(
    resid: torch.Tensor, m: int, dsub: int, ksub: int, *, niter: int, seed: int
) -> torch.Tensor:
    """Train ``m`` independent k-means sub-quantizers on residual sub-vectors.

    ``resid`` is ``(N, m*dsub)``; returns ``(m, ksub, dsub)`` fp32 codebooks.
    """
    resid_sub = resid.reshape(resid.shape[0], m, dsub)          # (N, m, dsub)
    codebooks = torch.empty(m, ksub, dsub, dtype=torch.float32, device=resid.device)
    for s in range(m):
        codebooks[s] = _lloyd_kmeans(resid_sub[:, s, :], ksub, niter=niter, seed=seed + s)
    return codebooks


def _encode_pq(
    resid: torch.Tensor, codebooks: torch.Tensor, m: int, dsub: int,
    chunk: int = 8192,
) -> torch.Tensor:
    """Encode residual rows to ``(N, m)`` uint8 PQ codes (nearest sub-centroid)."""
    N = resid.shape[0]
    resid_sub = resid.reshape(N, m, dsub)                       # (N, m, dsub)
    codes = torch.empty(N, m, dtype=torch.uint8, device=resid.device)
    for s in range(m):
        cb = codebooks[s].to(torch.float32)                    # (ksub, dsub)
        sub = resid_sub[:, s, :].to(torch.float32)             # (N, dsub)
        for lo in range(0, N, chunk):
            hi = min(lo + chunk, N)
            d2 = torch.cdist(sub[lo:hi], cb) ** 2              # (chunk, ksub)
            codes[lo:hi, s] = d2.argmin(dim=1).to(torch.uint8)
    return codes


# ── public build / search ──────────────────────────────────────────────────
def ivf_pq_build(
    X: torch.Tensor,
    nlist: int,
    *,
    m: int = 8,
    nbits: int = 8,
    metric: str = "l2",
    by_residual: bool = True,
    nprobe: int = 8,
    niter: int = 20,
    pq_niter: int = 25,
    train_size: Optional[int] = None,
    pq_train_size: Optional[int] = None,
    seed: int = 0,
):
    """Build an :class:`IvfPqIndex` with pure torch ops."""
    if metric != "l2":
        raise NotImplementedError(f"ivf_pq supports metric='l2' only (got {metric!r})")
    if nbits != 8:
        raise NotImplementedError(f"ivf_pq supports nbits=8 only (got {nbits})")
    if X.ndim != 2:
        raise ValueError("ivf_pq build expects a 2D (M, D) tensor")

    M, D = X.shape
    nlist = int(min(nlist, M))
    if nlist < 1:
        raise ValueError("nlist must be >= 1")
    m, dsub, Dp = _pq_dims(int(D), m)
    ksub = 1 << nbits                                            # 256
    Xp = _pad_features(X.to(torch.float32), Dp).contiguous()

    # ── coarse quantizer: k-means on a sample ──────────────────────────
    train_size = int(train_size or min(M, nlist * 256))
    train_size = max(min(train_size, M), nlist)
    g = torch.Generator(device="cpu").manual_seed(seed)
    sample_idx = torch.randperm(M, generator=g)[:train_size].to(X.device)
    sample = Xp.index_select(0, sample_idx)
    centroids = _lloyd_kmeans(sample, nlist, niter=niter, seed=seed)   # (nlist, Dp)

    # ── PQ codebooks from residuals of a (sub)sample ───────────────────
    pq_train_size = int(pq_train_size or min(train_size, max(ksub * 16, 4096)))
    pq_train_size = max(min(pq_train_size, train_size), ksub)
    pq_sample = sample[:pq_train_size]
    if by_residual:
        pq_assign = _assign_chunked(pq_sample, centroids)
        resid_train = pq_sample - centroids.index_select(0, pq_assign)
    else:
        resid_train = pq_sample
    codebooks = _train_pq_codebooks(
        resid_train, m, dsub, ksub, niter=pq_niter, seed=seed + 1
    )                                                            # (m, ksub, dsub)

    # ── assign every database row + encode its residual ────────────────
    assign = _assign_chunked(Xp, centroids)                     # (M,)
    resid_all = Xp - centroids.index_select(0, assign) if by_residual else Xp
    codes = _encode_pq(resid_all, codebooks, m, dsub)           # (M, m) uint8

    # ── CSR cell-contiguous layout ─────────────────────────────────────
    counts = torch.bincount(assign, minlength=nlist)            # (nlist,)
    offsets = torch.zeros(nlist + 1, dtype=torch.int64, device=X.device)
    offsets[1:] = counts.cumsum(0)
    order = torch.argsort(assign, stable=True)                  # (M,) int64
    codes_sorted = codes.index_select(0, order).contiguous()

    return IvfPqIndex(
        centroids=centroids,
        pq_codebooks=codebooks,
        codes=codes_sorted,
        ids=order.to(torch.int64),
        list_offsets=offsets,
        metric=metric,
        by_residual=bool(by_residual),
        D=int(D),
        Dp=int(Dp),
        dsub=int(dsub),
        m=int(m),
        nbits=int(nbits),
        nlist=int(nlist),
        nprobe=int(nprobe),
        max_list_len=int(counts.max().item()) if nlist > 0 else 0,
    )


__all__ = ["ivf_pq_build", "_pad_features", "_pq_dims"]
