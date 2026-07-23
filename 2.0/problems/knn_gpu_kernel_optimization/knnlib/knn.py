"""Brute-force squared-L2 k-nearest-neighbours -- the reference you must optimise.

This implementation is intentionally naive. It computes the full ``(Q, M)``
pairwise distance matrix with :func:`torch.cdist` and materialises it in HBM,
then runs :func:`torch.topk` over the whole matrix to pick the ``k`` nearest
database points for every query. It is correct and deterministic, but it moves
far more memory than necessary (the entire ``(Q, M)`` matrix) and cannot scale
to large ``M`` without exhausting device memory.

Contract (do NOT change):

    knn(queries, database, k) -> (distances, indices)

    queries   : (Q, D) float32 CUDA tensor of query points.
    database  : (M, D) float32 CUDA tensor of database points to search.
    k         : int, number of nearest neighbours to return per query.

    distances : (Q, k) float32 tensor of the SQUARED-L2 distances to the ``k``
                nearest database points, in ascending order (nearest first).
    indices   : (Q, k) int64 tensor of the corresponding database row indices.

You may add modules/kernels inside the ``knnlib`` package and rewrite the body
of :func:`knn` freely (fused/streamed running top-k, tiled distance kernels,
Triton), as long as the public contract above is preserved. In particular you
should avoid ever materialising the full ``(Q, M)`` distance matrix.
"""
from __future__ import annotations

import torch


def knn(queries, database, k):
    """Return the (squared-L2) k nearest database points for each query.

    Naive: materialise the full (Q, M) distance matrix, then top-k.
    """
    d2 = torch.cdist(queries, database) ** 2            # (Q, M), materialized -- naive
    dist, idx = torch.topk(d2, k, dim=1, largest=False)
    return dist, idx.to(torch.long)
