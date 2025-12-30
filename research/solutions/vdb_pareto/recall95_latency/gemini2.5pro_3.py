import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction for HNSW)
        """
        self.dim = dim
        
        # HNSW parameters are chosen to prioritize high recall while remaining fast.
        # M: Number of neighbors per node in the graph. Higher is better for recall.
        self.M = int(kwargs.get("M", 64))
        # efConstruction: Quality of the graph build. Higher is better but slower.
        self.efConstruction = int(kwargs.get("efConstruction", kwargs.get("ef_construction", 400)))
        # efSearch: Search-time quality/speed tradeoff. Higher is more accurate.
        self.efSearch = int(kwargs.get("efSearch", kwargs.get("ef_search", 128)))

        # The evaluation environment has 8 vCPUs. This enables multi-threading.
        faiss.omp_set_num_threads(8)

        # IndexHNSWFlat is a state-of-the-art graph-based index for CPU.
        # It provides excellent recall-speed trade-off without data compression.
        # METRIC_L2 is the default and correct metric for SIFT1M.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.efConstruction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # Faiss requires float32 data.
        if xb.dtype != np.float32:
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
        # Faiss requires float32 data.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set the search-time parameter.
        self.index.hnsw.efSearch = self.efSearch
        
        # Perform the search and return distances and indices.
        # Faiss returns L2-squared distances for METRIC_L2, which is acceptable
        # per the problem statement and faster than computing the square root.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices