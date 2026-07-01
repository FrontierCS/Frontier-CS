"""kmeanslib -- a tiny GPU K-Means library you are asked to make fast.

The public entry point is :func:`kmeans`. The shipped implementation is
correct but deliberately unoptimised. Your task is to rewrite the internals
(new Triton kernels, fused passes, better memory traffic, ...) so that
:func:`kmeans` runs as fast as possible while producing clusterings of the
same quality. The public function signature and return contract must not
change.
"""
from __future__ import annotations

from kmeanslib.kmeans import kmeans

__all__ = ["kmeans"]
__version__ = "0.1.0"
