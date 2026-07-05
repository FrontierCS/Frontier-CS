"""Frozen naive one-step K-Means baseline used by the judge as the speed
denominator. Behaviourally identical to the shipped ``kmeanslib.kmeans``
(``step`` + ``_assign`` + ``_update``); imported under its own module name so the
judge worker can load the frozen baseline and the patched ``kmeanslib`` package
in one process. The judge owns the Lloyd loop and calls ``step`` a fixed number
of times.
"""
from __future__ import annotations

import torch


def _assign(x: torch.Tensor, centroids: torch.Tensor) -> torch.Tensor:
    c = centroids.to(x.dtype)
    c_sq = (c.float() * c.float()).sum(1)
    labels = torch.empty(x.shape[0], device=x.device, dtype=torch.long)
    for lo in range(0, x.shape[0], 16384):
        xb = x[lo:lo + 16384]
        dist = c_sq[None, :] - 2.0 * (xb @ c.t()).float()   # bf16 matmul, fp32 accum
        labels[lo:lo + 16384] = torch.argmin(dist, dim=1)
    return labels


def _update(x: torch.Tensor, labels: torch.Tensor, n_clusters: int,
            old_centroids: torch.Tensor) -> torch.Tensor:
    N, D = x.shape
    sums = torch.zeros((n_clusters, D), device=x.device, dtype=torch.float32)
    counts = torch.zeros((n_clusters,), device=x.device, dtype=torch.float32)
    sums.index_add_(0, labels, x.float())
    counts.index_add_(0, labels, torch.ones(N, device=x.device, dtype=torch.float32))
    empty = counts == 0
    counts = counts.clamp_min(1.0)
    new = sums / counts[:, None]
    if empty.any():
        new[empty] = old_centroids[empty].float()
    return new.to(x.dtype)


def step(x: torch.Tensor, centroids: torch.Tensor):
    if x.ndim != 2:
        raise ValueError(f"x must be 2-D (N, D); got shape {tuple(x.shape)}")
    labels = _assign(x, centroids)
    new_centroids = _update(x, labels, centroids.shape[0], centroids)
    return labels, new_centroids
