import numpy as np
import faiss
import os
from typing import Tuple, Optional

class FaissHNSWIndex:
    """
    A FAISS-based HNSW index optimized for high recall under a strict latency constraint.

    This implementation uses the Hierarchical Navigable Small World (HNSW) graph-based
    index from FAISS. HNSW is chosen for its excellent speed-recall trade-off,
    especially on CPU-only environments.

    The key to meeting the strict latency requirement (t_query <= 2.31ms) is aggressive
    tuning of the `efSearch` parameter. A lower `efSearch` value reduces the number of
    graph nodes visited during a query, significantly speeding up the search at the
    cost of some recall.

    Parameter Justification:
    - M (default=32): The number of bidirectional links created for each new element
      during construction. 32 is a common and effective value for datasets like SIFT1M,
      providing a well-connected graph without excessive memory usage.
    - efConstruction (default=200): A high value for `efConstruction` is used to build a
      high-quality graph. The build time is a one-off cost, so optimizing for graph
      quality is prioritized, which helps maintain recall even with a low `efSearch`.
    - efSearch (default=64): This is the most critical parameter for this problem. The
      default value of 64 is chosen to be aggressively low to ensure the search latency
      remains well below the 2.31ms threshold. It strikes a balance between speed and
      recall, aiming to maximize score by first satisfying the latency gate.
    - Multi-threading: The implementation automatically sets the number of OpenMP threads
      used by FAISS to the number of available CPU cores. This is crucial for achieving
      low latency on batch queries by parallelizing the search process.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters for HNSW index.
                - M: Number of connections per node (default: 32).
                - ef_construction: Build-time search depth (default: 200).
                - ef_search: Query-time search depth (default: 64).
        """
        # Set the number of threads for FAISS to leverage all available CPU cores.
        # This is critical for fast batch processing.
        try:
            num_threads = os.cpu_count()
            if num_threads:
                faiss.omp_set_num_threads(num_threads)
        except (NotImplementedError, AttributeError):
            # Fallback if os.cpu_count() is not available
            pass

        self.dim: int = dim
        self.is_trained: bool = False
        
        # Extract HNSW parameters from kwargs or use optimized defaults
        M = kwargs.get('M', 32)
        ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 64)

        # Initialize the HNSW index. METRIC_L2 corresponds to Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        
        # Set the construction-time parameter.
        self.index.hnsw.efConstruction = ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if xb.shape[1] != self.dim:
            raise ValueError(f"Input vector dimension {xb.shape[1]} does not match index dimension {self.dim}")

        # FAISS requires float32 data.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        self.index.add(xb)
        self.is_trained = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: L2 distances, shape (nq, k), dtype float32.
                - indices: Indices of nearest neighbors, shape (nq, k), dtype int64.
        """
        if not self.is_trained:
            raise RuntimeError("Index has not been built. Please call add() first.")
        
        if xq.shape[1] != self.dim:
            raise ValueError(f"Query vector dimension {xq.shape[1]} does not match index dimension {self.dim}")

        # Set the search-time parameter. This is the main knob for the speed/recall trade-off.
        self.index.hnsw.efSearch = self.ef_search

        # FAISS requires float32 data for queries as well.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Perform the search.
        distances, indices = self.index.search(xq, k)

        return distances, indices

# To conform to the problem's discovery mechanism, we can provide an alias
# or simply rely on the fact that any class with the right methods will be found.
LowLatencyTierIndex = FaissHNSWIndex