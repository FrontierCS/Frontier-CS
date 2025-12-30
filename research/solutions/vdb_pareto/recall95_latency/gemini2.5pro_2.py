import numpy as np
import faiss
from typing import Tuple
import os

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction for HNSW)
        """
        self.dim = dim
        
        # Hyperparameters for HNSW, tuned for high recall and low latency on SIFT1M.
        # M: Number of neighbors in the HNSW graph. A larger M creates a denser
        #    graph, improving recall at the cost of memory and build time.
        # ef_construction: Build-time parameter. A larger value creates a higher
        #                  quality graph, leading to better search performance.
        # ef_search: Search-time parameter. This is the primary knob for the
        #            speed/recall trade-off. Higher values mean more exhaustive
        #            search, increasing recall and latency.
        self.M = kwargs.get('M', 32)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 80)

        # Configure FAISS to leverage all available CPU cores for parallel execution.
        # This is crucial for achieving low latency on batch queries.
        try:
            # os.sched_getaffinity is the most reliable way on Linux to get
            # the number of available CPUs.
            num_threads = len(os.sched_getaffinity(0))
        except AttributeError:
            # Fallback for non-Linux systems.
            num_threads = os.cpu_count() or 8
        faiss.omp_set_num_threads(num_threads)

        # We use IndexHNSWFlat, a state-of-the-art graph-based index that provides
        # excellent performance for high-recall scenarios.
        # We use METRIC_L2 for squared Euclidean distance, which is faster to
        # compute than L2 and is explicitly permitted by the problem statement.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # FAISS requires float32 input.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        # HNSW supports incremental additions.
        self.index.add(xb)

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
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set the search-time parameter to control the speed/accuracy trade-off.
        self.index.hnsw.efSearch = self.ef_search

        # The search method returns squared L2 distances and the indices of neighbors.
        # Returning squared distances is faster and sufficient for ranking.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices