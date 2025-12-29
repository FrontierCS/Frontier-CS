import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An HNSW-based index optimized for high recall under a relaxed latency constraint.

    This implementation uses FAISS's IndexHNSWFlat, which is a graph-based
    Approximate Nearest Neighbor (ANN) search algorithm. It is chosen for its
    excellent speed-recall trade-off on CPU-only environments.

    Strategy for High Recall Tier:
    1.  **Algorithm Choice**: HNSW (Hierarchical Navigable Small Worlds) is
        state-of-the-art for high-recall ANN search. IndexHNSWFlat is used to
        store full, uncompressed vectors, avoiding any quantization error and
        maximizing potential recall.

    2.  **High-Quality Graph Construction**:
        - `M=64`: A high connectivity parameter (`M`) creates a dense and robust
          graph. This improves search accuracy at the cost of higher memory usage
          and build time, both of which are acceptable within the given limits
          (16GB RAM, 1-hour build time).
        - `efConstruction=500`: A large search depth during index construction
          ensures that newly added points are linked into the graph optimally,
          leading to a higher-quality index structure for searching.

    3.  **Exhaustive Search**:
        - `efSearch=750`: The key to this solution is a very high search-time
          parameter (`efSearch`). The problem provides a generous latency budget
          of 7.7ms, which is double the baseline's 3.85ms. Assuming the baseline
          uses a balanced `efSearch` (e.g., ~300), we can afford a much larger
          value. `efSearch=750` is chosen to aggressively trade latency for
          recall, pushing recall well above the 0.9914 baseline to secure a
          maximum score, while staying within the 7.7ms time limit on the
          8-vCPU evaluation machine. FAISS's HNSW implementation is highly
          parallelized and will effectively use all available CPU cores.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M).
            **kwargs: Optional parameters to override HNSW settings.
        """
        self.dim = dim
        
        # Parameters are tuned for the high-recall objective and 7.7ms latency budget.
        self.M = kwargs.get('M', 64) 
        self.ef_construction = kwargs.get('ef_construction', 500)
        self.ef_search = kwargs.get('ef_search', 750) 
        
        # Initialize the HNSW index with L2 distance metric.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # FAISS automatically leverages multiple CPU cores for building and searching.
        # No explicit thread management is needed as it defaults to using all available threads.

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. This method can be called multiple times.
        FAISS HNSW builds the index incrementally as vectors are added.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # FAISS operates on float32 arrays.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for the k nearest neighbors for each query vector.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: L2-squared distances, shape (nq, k), dtype float32.
                - indices: 0-based indices of neighbors, shape (nq, k), dtype int64.
        """
        # Ensure query vectors are float32.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time parameter for the desired recall/latency trade-off.
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform the search. FAISS returns L2-squared distances for METRIC_L2.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices