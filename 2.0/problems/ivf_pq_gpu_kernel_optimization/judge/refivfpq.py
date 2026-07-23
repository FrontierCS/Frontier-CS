"""``IvfPqIndex`` -- the in-memory container for a built IVF-PQ index.

Stores the database **cell-contiguous** (all vectors of inverted list ``c`` in
rows ``[list_offsets[c], list_offsets[c+1])``) and keeps only the ``(M, m)``
uint8 product-quantization codes, not the full vectors. ``ids[p]`` maps a stored
row back to the caller's original row id. Torch-only; no kernel import. Frozen judge baseline; do not edit.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import torch

@dataclass
class IvfPqIndex:
    """A built IVF-PQ index.

    Attributes:
        centroids: ``(nlist, Dp)`` coarse-quantizer centroids (fp32).
        pq_codebooks: ``(m, ksub, dsub)`` product-quantization sub-centroids
            (fp32). ``ksub == 2**nbits`` (256 for the only supported
            ``nbits=8``); ``dsub == Dp // m``.
        codes: ``(M, m)`` uint8 -- per sub-quantizer code, cell-contiguous.
        ids: ``(M,)`` int64 -- original row id for each stored row.
        list_offsets: ``(nlist + 1,)`` int64 CSR offsets into ``codes``.
        metric: distance metric (only ``"l2"`` supported).
        by_residual: if True, PQ encodes ``x - centroid[list]`` (FAISS /
            cuVS default, higher recall); else PQ encodes ``x`` directly.
        D: original feature dimension as passed by the caller.
        Dp: padded working dimension (``m * dsub``, ``>= 16``); zero
            columns added for ``D < Dp`` never affect squared-L2 distances.
        dsub: sub-vector dimension (``Dp // m``).
        m: number of sub-quantizers (PQ codes per vector).
        nbits: bits per code (only ``8`` supported -> ``ksub = 256``).
        nlist: number of inverted lists / coarse centroids.
        nprobe: default number of lists to probe at search time.
        max_list_len: longest inverted list, recorded at build time so
            search can size the kernel's chunk loop without a D2H sync.
    """

    centroids: torch.Tensor
    pq_codebooks: torch.Tensor
    codes: torch.Tensor
    ids: torch.Tensor
    list_offsets: torch.Tensor
    metric: str
    by_residual: bool
    D: int
    Dp: int
    dsub: int
    m: int
    nbits: int
    nlist: int
    nprobe: int
    max_list_len: int = 0

    @property
    def ksub(self) -> int:
        """Number of sub-centroids per sub-quantizer (``2**nbits``)."""
        return int(self.pq_codebooks.shape[1])

    @property
    def M(self) -> int:
        return int(self.codes.shape[0])

    @property
    def device(self) -> torch.device:
        return self.codes.device

    @property
    def dtype(self) -> torch.dtype:
        """Working dtype of the centroids / codebooks (codes are uint8)."""
        return self.centroids.dtype

    def list_lengths(self) -> torch.Tensor:
        """``(nlist,)`` int64 number of vectors in each inverted list."""
        return self.list_offsets[1:] - self.list_offsets[:-1]

    def code_size_bytes(self) -> int:
        """Bytes per stored vector (``m`` for ``nbits=8``)."""
        return int(self.m)

    def compression_ratio(self) -> float:
        """Original fp32 vector bytes / PQ code bytes (storage savings)."""
        return (4.0 * self.D) / max(self.code_size_bytes(), 1)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"IvfPqIndex(M={self.M}, D={self.D}, Dp={self.Dp}, m={self.m}, "
            f"dsub={self.dsub}, nbits={self.nbits}, nlist={self.nlist}, "
            f"nprobe={self.nprobe}, by_residual={self.by_residual}, "
            f"metric={self.metric!r}, dtype={self.dtype}, device={self.device})"
        )


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


def ivf_pq_search(index, Q: torch.Tensor, k: int, *, nprobe: Optional[int] = None):
    """Reference coarse + ADC IVF-PQ search over a built index.

    Returns ``(vals, ids)`` where ``vals[i, j]`` is the (approximate)
    squared-L2 distance to the ``j``-th nearest PQ reconstruction and
    ``ids`` are original row ids. Mirrors the Triton kernel exactly:
    probe the ``nprobe`` nearest lists, build the per-(query, list)
    residual LUT, score each member as the sum of ``m`` table lookups,
    keep the global top-``k``.
    """
    if Q.ndim != 2:
        raise ValueError("ivf_pq search expects a 2D (nq, D) query tensor")
    nprobe = int(nprobe or index.nprobe)
    nprobe = max(1, min(nprobe, index.nlist))
    nq = Q.shape[0]
    Dp, m, dsub = index.Dp, index.m, index.dsub

    Qp = _pad_features(Q.to(torch.float32), Dp)
    centroids = index.centroids.to(torch.float32)               # (nlist, Dp)
    codebooks = index.pq_codebooks.to(torch.float32)            # (m, ksub, dsub)
    codes = index.codes                                         # (M, m) uint8
    offsets = index.list_offsets

    coarse_d2 = torch.cdist(Qp, centroids) ** 2                 # (nq, nlist)
    probed = coarse_d2.topk(nprobe, dim=1, largest=False).indices  # (nq, nprobe)

    out_vals = torch.full((nq, k), float("inf"), device=Q.device, dtype=torch.float32)
    out_ids = torch.full((nq, k), -1, device=Q.device, dtype=torch.int64)

    for i in range(nq):
        cand_dists = []
        cand_ids = []
        for p in range(nprobe):
            c = int(probed[i, p].item())
            s0, e0 = int(offsets[c].item()), int(offsets[c + 1].item())
            if e0 <= s0:
                continue
            rq = (Qp[i] - centroids[c]) if index.by_residual else Qp[i]   # (Dp,)
            rq_sub = rq.reshape(m, dsub)                                  # (m, dsub)
            # LUT[s, j] = ||rq_s - codebook[s, j]||^2
            lut = ((rq_sub[:, None, :] - codebooks) ** 2).sum(-1)        # (m, ksub)
            cc = codes[s0:e0].to(torch.int64)                            # (L, m)
            # dist[l] = sum_s LUT[s, cc[l, s]]
            dist = lut.gather(1, cc.t().contiguous()).sum(0)             # (L,)
            cand_dists.append(dist)
            cand_ids.append(index.ids[s0:e0])
        if not cand_dists:
            continue
        dist = torch.cat(cand_dists)
        ids = torch.cat(cand_ids)
        kk = min(k, dist.shape[0])
        vals, sel = dist.topk(kk, largest=False)
        out_vals[i, :kk] = vals
        out_ids[i, :kk] = ids[sel]

    return out_vals, out_ids


__all__ = ["IvfPqIndex", "ivf_pq_build", "ivf_pq_search"]
