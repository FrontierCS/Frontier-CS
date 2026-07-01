"""tsvdlib -- a tiny GPU truncated-SVD library you are asked to make fast.

The public entry point is :func:`truncated_svd`. The shipped implementation is
correct but deliberately unoptimised: it computes the FULL SVD of the ``(N, D)``
matrix and slices off the top-k factors. Your task is to rewrite the internals
(Gram-matrix + top-k eigendecomposition, fused kernels, reduced memory traffic,
...) so that :func:`truncated_svd` runs as fast as possible while producing
factors of the same quality. The public function signature and return contract
must not change.
"""
from __future__ import annotations

from tsvdlib.tsvd import truncated_svd

__all__ = ["truncated_svd"]
__version__ = "0.1.0"
