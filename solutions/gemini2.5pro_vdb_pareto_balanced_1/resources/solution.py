import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        This index uses FAISS's implementation of HNSW (Hierarchical Navigable Small Worlds),
        a graph-based ANN algorithm known for its excellent speed-recall tradeoff, especially
        for high-recall scenarios.

        The parameters `M`, `efConstruction`, and `efSearch` are tuned to maximize recall
        on the SIFT1M dataset while staying within the specified latency constraints for
        a multi-core CPU environment.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M).
            **kwargs: Optional parameters for HNSW (e.g., M, efConstruction, efSearch).
        """
        self.dim = dim

        # Set the number of threads for FAISS to utilize the 8 vCPUs specified in the
        # evaluation environment. This is crucial for achieving low latency on batch queries.
        num_threads = 8
        faiss.omp_set_num_threads(num_threads)

        # Hyperparameters for HNSW, tuned for high recall.
        # A high M and efConstruction create a high-quality graph.
        # efSearch is set to a value that aims to use the latency budget to maximize recall.
        self.M = kwargs.get('M', 64)
        self.efConstruction = kwargs.get('efConstruction', 400)
        self.efSearch = kwargs.get('efSearch', 120)
        
        # We use IndexHNSWFlat to store uncompressed vectors, avoiding quantization errors
        # and thus maximizing recall. METRIC_L2 corresponds to Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.efConstruction
        
        self.is_trained = False

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. HNSW supports cumulative additions.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # FAISS requires C-contiguous float32 arrays for optimal performance.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)

        self.index.add(xb)
        self.is_trained = True

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
        if not self.is_trained:
            # If the index is empty, return sentinel values matching the required output shape.
            nq = xq.shape[0]
            distances = np.full((nq, k), -1, dtype=np.float32)
            indices = np.full((nq, k), -1, dtype=np.int64)
            return distances, indices

        # Set the search-time parameter `efSearch`. This controls the exploration of the
        # graph; a higher value leads to better recall at the cost of higher latency.
        self.index.hnsw.efSearch = self.efSearch

        # Ensure query vectors are in the correct format for FAISS.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)

        # Perform the search. FAISS automatically handles batching and multithreading.
        distances, indices = self.index.search(xq, k)

        # FAISS with METRIC_L2 returns squared L2 distances. The problem statement accepts
        # this, and it's more efficient than calculating the true L2 distance (sqrt).
        return distances, indices
