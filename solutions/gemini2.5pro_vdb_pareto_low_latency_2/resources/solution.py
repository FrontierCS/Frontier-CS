import numpy as np
import faiss
import os
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
        
        # These parameters are tuned for the SIFT1M dataset on an 8-core CPU
        # to meet the strict <2.31ms latency constraint while maximizing recall.
        # HNSW is chosen for its excellent speed-recall tradeoff.
        # M: Number of connections per node. Higher M creates a better quality graph.
        self.M = int(kwargs.get("M", 48))
        # efConstruction: Build-time parameter. Higher value means a better graph.
        self.efConstruction = int(kwargs.get("efConstruction", 200))
        # efSearch: Search-time parameter, the primary knob for latency vs recall.
        # This value is set aggressively to ensure latency is met.
        self.efSearch = int(kwargs.get("efSearch", 80))
        
        self.index = None
        self.is_built = False

        # Use all available CPU cores for FAISS to speed up batch search.
        try:
            num_threads = os.cpu_count()
            if num_threads:
                faiss.omp_set_num_threads(num_threads)
        except (AttributeError, TypeError):
            # Fallback for environments where os.cpu_count() is not available/reliable.
            pass
        
        # Initialize the HNSW index. METRIC_L2 corresponds to Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.efConstruction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # FAISS requires C-contiguous float32 arrays for optimal performance.
        if not xb.flags['C_CONTIGUOUS'] or xb.dtype != np.float32:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        
        # In HNSW, adding vectors is the build process.
        self.index.add(xb)
        self.is_built = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        if not self.is_built:
            raise RuntimeError("Index has not been built. Call add() first.")

        # Set the search-time parameter.
        self.index.hnsw.efSearch = self.efSearch

        if not xq.flags['C_CONTIGUOUS'] or xq.dtype != np.float32:
            xq = np.ascontiguousarray(xq, dtype=np.float32)

        distances, indices = self.index.search(xq, k)
        
        # Per the problem spec, L2-squared distances are acceptable.
        # Faiss's IndexHNSWFlat returns squared L2 distances by default,
        # which is faster as it avoids the sqrt operation.
        return distances, indices
