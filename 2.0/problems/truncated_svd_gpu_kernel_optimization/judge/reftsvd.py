"""Frozen naive truncated-SVD baseline used by the judge as the speed denominator.

This is a standalone (non-package) copy of the ``tsvdlib.truncated_svd``
implementation the agent starts from. It is imported under its own module name
so the judge worker can load the frozen baseline and the patched ``tsvdlib``
package in the same process. Keep this behaviourally identical to the shipped
``tsvdlib/tsvd.py`` (full SVD, then slice the top-k factors).
"""
from __future__ import annotations

import torch


def truncated_svd(x, n_components):
    U, S, Vh = torch.linalg.svd(x, full_matrices=False)   # full SVD -- naive/expensive
    return S[:n_components].contiguous(), Vh[:n_components].contiguous()
