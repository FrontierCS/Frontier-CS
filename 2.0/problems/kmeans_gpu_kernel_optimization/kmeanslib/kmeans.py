"""One Lloyd K-Means step -- the function you optimise.

The judge owns the iteration loop, the data, the initial centroids, and the
iteration count; you provide a single Lloyd step and it is called repeatedly.
This shipped step is intentionally naive (materialise a (chunk, K) distance
matrix with a bf16 matmul + argmin, then a PyTorch scatter update).

Contract (do NOT change):

    step(x, centroids) -> (labels, new_centroids)

    x            : (N, D) bfloat16 CUDA tensor of points.
    centroids    : (K, D) bfloat16 tensor -- the current centroids.
    labels       : (N,) int64 -- nearest-centroid assignment of every point to
                   `centroids` (a full assignment of all N points).
    new_centroids: (K, D) -- centroids recomputed as the mean of each cluster
                   (empty clusters keep their previous centroid).

This is exactly one Lloyd iteration: assign to `centroids`, then update. You may
add modules/kernels under ``kmeanslib`` and rewrite the body of ``step``,
``_assign`` and ``_update`` freely -- including **fusing the assign + update into
a single kernel** -- as long as ``step(x, centroids) -> (labels, new_centroids)``
is preserved. You cannot change how many times it runs, the data, or the initial
centroids; the judge owns the loop and calls ``step`` a fixed number of times.
"""
from __future__ import annotations

import torch


def _assign(x: torch.Tensor, centroids: torch.Tensor) -> torch.Tensor:
    """Nearest-centroid assignment by squared-L2 distance.

    Naive: for each chunk of points, materialise the (chunk, K) distance matrix
    with a bf16 matmul, then argmin. ``argmin ||x-c||^2 == argmin (||c||^2 - 2
    x.c^T)`` since ``||x||^2`` is constant per row. bf16 in, fp32 accumulation.
    """
    c = centroids.to(x.dtype)
    c_sq = (c.float() * c.float()).sum(1)                    # (K,) fp32
    labels = torch.empty(x.shape[0], device=x.device, dtype=torch.long)
    for lo in range(0, x.shape[0], 16384):
        xb = x[lo:lo + 16384]
        dist = c_sq[None, :] - 2.0 * (xb @ c.t()).float()   # (chunk, K) fp32
        labels[lo:lo + 16384] = torch.argmin(dist, dim=1)
    return labels


def _update(
    x: torch.Tensor,
    labels: torch.Tensor,
    n_clusters: int,
    old_centroids: torch.Tensor,
) -> torch.Tensor:
    """Recompute each centroid as the mean of its assigned points.

    Empty clusters keep their previous centroid.
    """
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
    """One Lloyd iteration: assign to `centroids`, then recompute them.

    Returns ``(labels, new_centroids)``. See the module docstring for the contract.
    """
    if x.ndim != 2:
        raise ValueError(f"x must be 2-D (N, D); got shape {tuple(x.shape)}")
    labels = _assign(x, centroids)
    new_centroids = _update(x, labels, centroids.shape[0], centroids)
    return labels, new_centroids
