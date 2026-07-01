"""Frozen naive PCA baseline used by the judge as the speed denominator.

This is a standalone (non-package) copy of the ``pcalib.pca`` implementation
the agent starts from. It is imported under its own module name so the judge
worker can load the frozen baseline and the patched ``pcalib`` package in the
same process. Keep this behaviourally identical to the shipped
``pcalib/pca.py``.
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
