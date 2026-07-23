"""GPU IVF-PQ library: naive torch baseline to be optimized (search) plus a
frozen index builder. Public API: ``ivf_pq_build``, ``ivf_pq_search``,
``IvfPqIndex``."""
from ivfpqlib.index import IvfPqIndex
from ivfpqlib.build import ivf_pq_build
from ivfpqlib.search import ivf_pq_search

__all__ = ["ivf_pq_build", "ivf_pq_search", "IvfPqIndex"]
