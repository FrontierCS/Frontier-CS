"""Naive DBSCAN baseline (correct, deterministic, GPU/CPU torch).

Euclidean DBSCAN. Chunked O(N^2) neighbour scan + GPU-friendly label
propagation for the connected components of the core graph. Border rule matches
flashlib: a non-core point joins the SMALLEST cluster label among its in-eps
core neighbours; otherwise it is noise (-1).
"""
from __future__ import annotations

import torch


def dbscan(x, eps, min_samples, max_neighbors=32):
    del max_neighbors  # naive path scans all neighbours; knob only for the fast kernel
    N = x.shape[0]
    dev = x.device
    eps2 = float(eps) * float(eps)
    xn = (x * x).sum(1)                          # (N,)
    CH = 4096
    BIG = N  # sentinel label (> any real label)

    def d2_chunk(lo, hi):
        xb = x[lo:hi]
        return (xb * xb).sum(1, keepdim=True) - 2.0 * (xb @ x.t()) + xn[None, :]

    # 1) degree (in-eps count, includes self) -> core mask
    deg = torch.zeros(N, device=dev, dtype=torch.int64)
    for lo in range(0, N, CH):
        hi = min(lo + CH, N)
        deg[lo:hi] = (d2_chunk(lo, hi) <= eps2).sum(1)
    core = deg >= int(min_samples)              # (N,) bool

    # 2) connected components of the core-core eps graph via label propagation
    labels = torch.arange(N, device=dev, dtype=torch.int64)
    labels[~core] = BIG
    for _ in range(1000):
        new = labels.clone()
        for lo in range(0, N, CH):
            hi = min(lo + CH, N)
            if not bool(core[lo:hi].any()):
                continue
            adj = (d2_chunk(lo, hi) <= eps2) & core[None, :]     # (chunk, N)
            lab = torch.where(adj, labels[None, :], torch.full((1, N), BIG, device=dev, dtype=torch.int64))
            mn = lab.min(1).values                                # (chunk,)
            rows = slice(lo, hi)
            upd = core[rows] & (mn < new[rows])
            new[rows] = torch.where(upd, mn, new[rows])
        if torch.equal(new, labels):
            break
        labels = new

    # 3) border assignment: non-core within eps of a core -> smallest core label
    for lo in range(0, N, CH):
        hi = min(lo + CH, N)
        nb = ~core[lo:hi]
        if not bool(nb.any()):
            continue
        adj = (d2_chunk(lo, hi) <= eps2) & core[None, :]
        lab = torch.where(adj, labels[None, :], torch.full((1, N), BIG, device=dev, dtype=torch.int64))
        mn = lab.min(1).values
        rows = slice(lo, hi)
        take = nb & (mn < BIG)
        labels[rows] = torch.where(take, mn, labels[rows])

    # 4) compact to dense [0, n_clusters); noise (BIG) -> -1
    out = torch.full((N,), -1, device=dev, dtype=torch.int64)
    uniq = torch.unique(labels[labels < BIG])
    for new_id, old in enumerate(uniq.tolist()):
        out[labels == old] = new_id
    return out
