"""Frozen naive K-Means baseline used by the judge as the speed denominator.

This is a standalone (non-package) copy of the ``kmeanslib.kmeans``
implementation the agent starts from. It is imported under its own module name
so the judge worker can load the frozen baseline and the patched ``kmeanslib``
package in the same process. Keep this behaviourally identical to the shipped
``kmeanslib/kmeans.py``.
"""
from __future__ import annotations

import torch


def _assign(x: torch.Tensor, centroids: torch.Tensor) -> torch.Tensor:
    # Naive per-chunk squared-L2: materialise (chunk, K) via a bf16 matmul, argmin.
    # argmin ||x-c||^2 == argmin (||c||^2 - 2 x.c^T); ||x||^2 is constant per row.
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


def kmeans(x, n_clusters, *, max_iters=10, init_centroids, tol=0.0):
    if x.ndim != 2:
        raise ValueError(f"x must be 2-D (N, D); got shape {tuple(x.shape)}")
    if init_centroids is None:
        raise ValueError("init_centroids is required")
    centroids = init_centroids.to(x.dtype).clone()
    labels = torch.zeros((x.shape[0],), device=x.device, dtype=torch.long)
    n_iter = 0
    for n_iter in range(max_iters):
        labels = _assign(x, centroids)
        new_centroids = _update(x, labels, n_clusters, centroids)
        shift = (new_centroids - centroids).norm(dim=-1).max()
        centroids = new_centroids
        if tol > 0.0 and float(shift) < tol:
            break
    return labels, centroids, n_iter + 1
