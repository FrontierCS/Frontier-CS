"""Principal Component Analysis (PCA) -- the reference you must optimise.

This implementation is intentionally naive. It centres the data by explicitly
materialising the full ``(N, D)`` centred matrix and then runs a *full* thin
SVD (:func:`torch.linalg.svd`) just to read off the top ``k`` singular vectors
and singular values. It is correct and deterministic, but it computes the
entire spectrum when only the leading ``k`` components are needed and it moves
far more memory than necessary (the centred copy of the whole dataset).

Contract (do NOT change):

    pca(x, n_components) -> (components, explained_variance)

    x               : (N, D) float32 CUDA tensor of points.
    n_components (k): int, number of leading principal components to return.

    components         : (k, D) float32 tensor whose rows are the top-k
                         principal axes (the leading eigenvectors of the
                         covariance matrix), orthonormal rows.
    explained_variance : (k,) float32 tensor of the corresponding covariance
                         eigenvalues, in descending order. With the unbiased
                         (``N - 1``) normalisation this equals
                         ``S[:k] ** 2 / (N - 1)`` for singular values ``S`` of
                         the centred data.

You may add modules/kernels inside the ``pcalib`` package and rewrite the body
of :func:`pca` freely (covariance/Gram + top-k eigendecomposition, fused
centring, Triton kernels, ...), as long as the public contract above is
preserved.
"""
from __future__ import annotations

import torch


def pca(x, n_components):
    N = x.shape[0]
    mean = x.mean(dim=0)
    xc = x - mean                                       # materialized centered matrix -- naive
    U, S, Vh = torch.linalg.svd(xc, full_matrices=False)  # full SVD -- expensive
    k = int(n_components)
    components = Vh[:k].contiguous()
    explained_variance = (S[:k] ** 2) / (N - 1)
    return components, explained_variance.contiguous()
