"""pcalib -- a tiny GPU PCA library you are asked to make fast.

The public entry point is :func:`pca`. The shipped implementation is correct
but deliberately unoptimised (it materialises the centred data matrix and runs
a full SVD). Your task is to rewrite the internals (covariance/Gram + top-k
eigendecomposition, fused centring, new Triton kernels, ...) so that
:func:`pca` runs as fast as possible while producing the same principal
subspace. The public function signature and return contract must not change.
"""
from __future__ import annotations

from pcalib.pca import pca

__all__ = ["pca"]
__version__ = "0.1.0"
