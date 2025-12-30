import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A FAISS-based high-recall vector index using HNSW (Hierarchical Navigable Small World).

    This index is optimized for recall, leveraging the relaxed latency constraint of the
    High Recall Tier. It uses the HNSWFlat index, which operates on the original,
    uncompressed vectors to avoid any loss of precision from quantization.

    The key tuning parameters are set to aggressive values to ensure a thorough search:
    - M: Number of neighbors in the HNSW graph. A higher value (64) creates a
      denser, more accurate graph.
    - ef_construction: Build-time search depth. A higher value (500) results in a
      higher quality index at the cost of longer build time.
    - ef_search: Search-time search depth. This is the most critical parameter for
      the recall/latency trade-off. It is set to a high value (800) to maximize
      recall within the given latency budget (7.7ms).

    The implementation assumes that the FAISS library is installed and compiled with
    OpenMP support to automatically leverage multiple CPU cores for batch searches.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW:
                - M: HNSW graph connectivity (default: 64)
                - ef_construction: HNSW build-time quality parameter (default: 500)
                - ef_search: HNSW search-time quality parameter (default: 800)
        """
        self.dim = dim

        # Use kwargs to allow for parameter tuning, but provide strong defaults
        # optimized for the high-recall tier.
        self.m = kwargs.get('M', 64)
        self.ef_construction = kwargs.get('ef_construction', 500)
        self.ef_search = kwargs.get('ef_search', 800)

        # faiss.IndexHNSWFlat stores the full vectors, which is ideal for maximizing recall.
        # It uses L2 distance as required by the SIFT1M dataset.
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        
        # Set the build-time parameter.
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Ensure input is float32, as required by FAISS.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances.
                - indices: shape (nq, k), dtype int64, indices into base vectors.
        """
        # Ensure query vectors are float32.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time parameter. This is the crucial knob for trading
        # speed for accuracy. We set it to a high value to maximize recall,
        # making use of the generous 7.7ms latency budget.
        self.index.hnsw.efSearch = self.ef_search

        # Perform the search. FAISS's HNSW implementation is highly optimized
        # for batch queries on multi-core CPUs.
        distances, indices = self.index.search(xq, k)

        return distances, indices