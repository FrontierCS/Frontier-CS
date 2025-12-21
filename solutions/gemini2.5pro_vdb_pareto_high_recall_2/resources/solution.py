import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW.
                      - M: Number of connections per node (default: 64)
                      - ef_construction: Build-time search depth (default: 512)
                      - ef_search: Query-time search depth (default: 512)
        """
        self.dim = dim
        self.m = kwargs.get('M', 64)
        self.ef_construction = kwargs.get('ef_construction', 512)
        self.ef_search = kwargs.get('ef_search', 512)
        
        # Use IndexHNSWFlat for high accuracy without compression.
        # It stores full vectors, which is feasible given the 16GB RAM constraint.
        # METRIC_L2 corresponds to squared Euclidean distance, which is acceptable.
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # FAISS requires float32 data type.
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
                - distances: shape (nq, k), dtype float32, squared L2 distances.
                - indices: shape (nq, k), dtype int64, indices into base vectors.
        """
        # Set the search-time parameter. This is the primary knob for the
        # speed/recall trade-off. The value is set aggressively to leverage
        # the relaxed latency constraint of 7.7ms for higher recall.
        self.index.hnsw.efSearch = self.ef_search
        
        # FAISS requires float32 data type.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        distances, indices = self.index.search(xq, k)
        
        return distances, indices
