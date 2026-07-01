"""Truncated SVD of a dense matrix -- the reference you must optimise.

This implementation is intentionally naive. It computes the FULL singular value
decomposition of the ``(N, D)`` matrix with :func:`torch.linalg.svd` and then
slices off the top ``n_components`` factors. Computing the full SVD is
``O(N D^2)`` with a large constant and produces all ``min(N, D)`` singular
triples even though only the leading ``k`` are ever used. It is correct and
deterministic, but it does far more work and moves far more memory than a
truncated decomposition needs.

Contract (do NOT change):

    truncated_svd(x, n_components) -> (singular_values, components)

    x               : (N, D) float32 CUDA tensor. NOT centered -- this is a
                      truncated SVD of the raw matrix, not PCA.
    n_components (k) : int, number of leading singular triples to return.

    singular_values : (k,) float32, the top-k singular values in DESCENDING
                      order.
    components       : (k, D) float32, the top-k right singular vectors as
                      rows. The rows are orthonormal.

You may add modules/kernels inside the ``tsvdlib`` package and rewrite the body
of :func:`truncated_svd` freely (e.g. a Gram-matrix + top-k eigendecomposition,
fused kernels, better memory traffic), as long as the public contract above is
preserved.
"""
from __future__ import annotations

import torch


def truncated_svd(x, n_components):
    U, S, Vh = torch.linalg.svd(x, full_matrices=False)   # full SVD -- naive/expensive
    return S[:n_components].contiguous(), Vh[:n_components].contiguous()
