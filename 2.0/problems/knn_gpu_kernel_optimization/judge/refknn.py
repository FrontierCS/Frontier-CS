"""Frozen naive brute-force k-NN baseline used by the judge.

This is a standalone (non-package) copy of the ``knnlib.knn`` implementation the
agent starts from. It is imported under its own module name so the judge worker
can load the frozen baseline and the patched ``knnlib`` package in the same
process. The judge uses it both as the speed denominator and as the exact
oracle from which the true k nearest neighbours (for the recall@k gate) are
recomputed. Keep this behaviourally identical to the shipped ``knnlib/knn.py``.
"""
from __future__ import annotations

import torch


def knn(queries, database, k):
    d2 = torch.cdist(queries, database) ** 2            # (Q, M), materialized -- naive
    dist, idx = torch.topk(d2, k, dim=1, largest=False)
    return dist, idx.to(torch.long)
