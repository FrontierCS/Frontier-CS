"""dbscanlib -- a tiny GPU DBSCAN you are asked to make fast.

The shipped implementation is correct but naive (chunked O(N^2) neighbour scan +
label propagation). Rewrite the internals (grid/bucketed radius search, fused
neighbour + connected-components kernels, ...) to make :func:`dbscan` fast while
producing the same clustering. The public signature/return must not change.
"""
from __future__ import annotations
from dbscanlib.dbscan import dbscan
__all__ = ["dbscan"]
__version__ = "0.1.0"
