import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An HNSW-based index optimized for high recall under a strict latency constraint.

    This implementation uses Faiss's `IndexHNSWFlat` for its excellent performance
    and recall-vs-speed trade-off on CPU. The hyperparameters are aggressively tuned
    to maximize recall for the SIFT1M dataset, aiming to stay just under the
    5.775ms latency limit in the specified 8-core CPU environment.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW configuration.
                - M (int): Connections per node in the graph. Default: 48.
                - ef_construction (int): Build-time search depth. Default: 512.
                - ef_search (int): Query-time search depth. Default: 768.
                - num_threads (int): CPU threads for Faiss. Default: 8.
        """
        self.dim = dim
        
        # Hyperparameters chosen for high recall on SIFT1M
        self.M = kwargs.get('M', 48)
        self.ef_construction = kwargs.get('ef_construction', 512)
        self.ef_search = kwargs.get('ef_search', 768)
        num_threads = kwargs.get('num_threads', 8)

        # Set Faiss to use the number of available vCPUs for parallelization
        faiss.omp_set_num_threads(num_threads)

        # IndexHNSWFlat uses an HNSW graph to find candidate vectors and then
        # computes exact L2 distances for refinement. This provides high accuracy.
        # METRIC_L2 is the specified distance metric (Euclidean).
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        
        # Set build-time and search-time parameters
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # Faiss requires C-contiguous float32 arrays.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
            
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
        if self.index.ntotal == 0:
            # Return empty arrays if index is not built
            nq = xq.shape[0]
            return np.full((nq, k), -1, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # Ensure query vectors are in the correct format for Faiss
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)

        # Faiss HNSW search returns L2-squared distances, which is permitted by
        # the problem spec ("L2 or L2-squared") and avoids a costly sqrt operation.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
