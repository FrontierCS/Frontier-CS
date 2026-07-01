"""Euclidean (squared-L2) Lloyd K-Means -- the reference you must optimise.

This implementation is intentionally naive. Every Lloyd iteration it
materialises the full ``(N, K)`` distance matrix with :func:`torch.cdist`
and recomputes the assignment and the centroid update with plain PyTorch
scatter ops. It is correct and deterministic, but it moves far more memory
than necessary and launches many small kernels.

Contract (do NOT change):

    kmeans(x, n_clusters, *, max_iters, init_centroids, tol=0.0)
        -> (labels, centroids, n_iter)

    x               : (N, D) float32 CUDA tensor of points.
    n_clusters (K)  : int, number of clusters.
    max_iters       : int, number of Lloyd iterations (fixed by the caller).
    init_centroids  : (K, D) tensor -- REQUIRED. The initial centroids. The
                      caller always supplies these so the result is a
                      deterministic function of (x, init_centroids, max_iters).
    tol             : float. If > 0, stop early once the maximum centroid
                      shift drops below ``tol``. The grader always calls with
                      ``tol=0.0`` (run all ``max_iters`` iterations).

    labels          : (N,) int64 cluster id per point (assignment at the start
                      of the final iteration).
    centroids       : (K, D) float32 final centroids (after the final update).
    n_iter          : int, number of iterations actually run.

You may add modules/kernels inside the ``kmeanslib`` package and rewrite the
body of :func:`kmeans`, ``_assign`` and ``_update`` freely, as long as the
public contract above is preserved.
"""
from __future__ import annotations

import torch


def _assign(x: torch.Tensor, centroids: torch.Tensor) -> torch.Tensor:
    """Nearest-centroid assignment by squared-L2 distance.

    Naive: materialise the full (N, K) distance matrix, then argmin.
    """
    # torch.cdist returns Euclidean distance; argmin of distance == argmin of
    # squared distance, so we do not bother squaring.
    dist = torch.cdist(x, centroids.to(x.dtype))  # (N, K)
    return torch.argmin(dist, dim=1)


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


def kmeans(
    x: torch.Tensor,
    n_clusters: int,
    *,
    max_iters: int = 10,
    init_centroids: torch.Tensor,
    tol: float = 0.0,
):
    """Lloyd K-Means with fixed initial centroids. See module docstring."""
    if x.ndim != 2:
        raise ValueError(f"x must be 2-D (N, D); got shape {tuple(x.shape)}")
    if init_centroids is None:
        raise ValueError("init_centroids is required (deterministic initialisation)")

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
