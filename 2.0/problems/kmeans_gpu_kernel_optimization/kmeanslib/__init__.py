"""kmeanslib -- a tiny GPU K-Means library you are asked to make fast.

The public entry point is :func:`step`, one Lloyd iteration
``step(x, centroids) -> (labels, new_centroids)``. The judge owns the iteration
loop and calls it a fixed number of times. The shipped implementation is correct
but deliberately unoptimised. Rewrite the internals (new Triton kernels, a fused
assign+update pass, better memory traffic, ...) so that ``step`` runs as fast as
possible while producing the same clustering. The public function signature and
return contract must not change.
"""
from __future__ import annotations

from kmeanslib.kmeans import step

__all__ = ["step"]
__version__ = "0.1.0"
