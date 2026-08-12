"""knnlib -- a tiny GPU brute-force k-NN library you are asked to make fast.

The public entry point is :func:`knn`. The shipped implementation is correct
but deliberately unoptimised: it materialises the full ``(Q, M)`` pairwise
distance matrix before selecting the ``k`` nearest neighbours. Your task is to
rewrite the internals (new Triton kernels, fused/streamed top-k passes, better
memory traffic, ...) so that :func:`knn` runs as fast as possible while
returning the same nearest neighbours. The public function signature and return
contract must not change.
"""
from __future__ import annotations

from knnlib.knn import knn

__all__ = ["knn"]
__version__ = "0.1.0"
