import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A FAISS-based index for the Balanced Tier VDB design problem.

    This implementation uses Hierarchical Navigable Small Worlds (HNSW)
    implemented in the FAISS library. HNSW is chosen for its excellent
    speed-recall performance, especially in high-recall scenarios on
    CPU-only environments.

    The strategy is to use `IndexHNSWFlat`, which stores full, uncompressed
    vectors. This avoids any recall loss from quantization, which is critical
    as the primary goal is to maximize recall. The SIFT1M dataset is small
    enough (~500MB) to fit comfortably within the 16GB RAM limit.

    Parameters have been carefully tuned to maximize recall@1 while respecting
    the hard latency constraint of 5.775ms per query.

    - M = 48: A high value for graph connectivity. This creates a denser,
      higher-quality graph, which is the foundation for high recall.
    - efConstruction = 400: A high value for build-time search depth. This
      ensures the HNSW graph is constructed to a very high quality, improving
      the probability of finding the true nearest neighbors.
    - efSearch = 128: A robust and high-quality search-time parameter. It
      defines the size of the candidate list during search. This value is
      chosen to be aggressive enough to surpass the baseline recall of 0.9914,
      while being conservative enough to reliably stay under the 5.775ms
      latency threshold.
    - Parallelization: The implementation leverages all 8 vCPUs available in
      the evaluation environment via `faiss.omp_set_num_threads(8)` to
      accelerate both index construction (`add`) and batch searching (`search`).
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (ignored in favor of pre-tuned values)
        """
        self.dim = dim
        
        # Tuned HNSW parameters for high recall under the latency constraint.
        M = 48
        ef_construction = 400
        ef_search = 128

        # Initialize the FAISS Index using HNSW on uncompressed vectors.
        # METRIC_L2 corresponds to Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        
        # Set FAISS to use all available CPU cores for parallel execution.
        # The evaluation environment specifies 8 vCPUs.
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # FAISS C++ backend requires float32 data.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        # Add vectors to the HNSW graph. HNSW does not have a separate
        # training step; the graph is built as data is added.
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
        # Ensure query vectors are float32 for FAISS.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        # Perform the search. The `efSearch` parameter, which controls the
        # speed-recall trade-off, was set during initialization.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices