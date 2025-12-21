import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW index.
                - M: Number of neighbors for each node in the HNSW graph (default: 48).
                - ef_construction: Search depth during index construction (default: 200).
                - ef_search: Search depth at query time (default: 80).
        """
        self.dim = dim
        
        # HNSW parameters are chosen to balance high recall and low latency.
        # M=48 creates a dense, high-quality graph.
        # ef_construction=200 ensures the graph quality during build time.
        # ef_search=80 is a tuned value aiming for >95% recall with low latency.
        self.M = int(kwargs.get('M', 48))
        self.ef_construction = int(kwargs.get('ef_construction', 200))
        self.ef_search = int(kwargs.get('ef_search', 80))
        
        # Use faiss.IndexHNSWFlat for high accuracy without vector compression.
        # METRIC_L2 is used for Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # Ensure input data is C-contiguous and float32 for FAISS compatibility.
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        elif xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        # Set the search-time parameter to control the speed/accuracy trade-off.
        self.index.hnsw.efSearch = self.ef_search

        # Ensure query vectors are in the correct format for FAISS.
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        elif xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        # Perform the search. FAISS HNSW returns L2-squared distances by default
        # for L2 metric, which is faster and acceptable by the problem statement.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
