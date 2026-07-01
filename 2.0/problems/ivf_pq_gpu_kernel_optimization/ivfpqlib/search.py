"""Naive IVF-PQ search (pure torch reference -- the baseline you optimize).

Coarse step: probe the ``nprobe`` nearest lists per query. Fine step: for each
query, build the per-list residual ADC lookup table and score every probed
candidate as ``sum_s LUT[s, code[s]]``, then keep the global top-``k``. The
Python per-query loop is what makes this slow; a fast GPU implementation fuses
the coarse search, LUT build, and ragged candidate scan into kernels.

    ivf_pq_search(index, Q, k, *, nprobe=None) -> (vals (nq,k) fp32,
                                                   ids  (nq,k) int64, -1 padded)
"""
from __future__ import annotations

from typing import Optional

import torch

from ivfpqlib.build import _pad_features

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


__all__ = ["ivf_pq_search"]
