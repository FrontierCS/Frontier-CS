import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A Vector Database index optimized for latency under a high recall constraint.
    This implementation uses Faiss's HNSW (Hierarchical Navigable Small Worlds)
    graph-based index, which is state-of-the-art for CPU-based high-recall,
    low-latency approximate nearest neighbor search.

    The parameters (M, ef_construction, ef_search) are tuned specifically for
    the SIFT1M dataset and the Recall95 Latency Tier problem constraints.
    - A high-quality graph is built (M=48, ef_construction=400) to maximize the
      potential for high recall. This is feasible due to the generous build time limit.
    - The search-time parameter (ef_search=160) is carefully chosen to be
      aggressive enough to yield low latency while being conservative enough to
      safely exceed the 95% recall@1 threshold.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters to override HNSW settings.
                      Supported keys: "M", "ef_construction", "ef_search".
        """
        self.dim = dim
        
        self.m = kwargs.get("M", 48)
        self.ef_construction = kwargs.get("ef_construction", 400)
        self.ef_search = kwargs.get("ef_search", 160)
        
        # Use IndexHNSWFlat for maximum accuracy without compression.
        # SIFT1M fits in memory, so no quantization is needed.
        # METRIC_L2 computes squared Euclidean distances, which is order-preserving
        # and thus valid for nearest neighbor search.
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Faiss HNSW builds the graph incrementally.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Faiss requires float32 and C-contiguous arrays for optimal performance.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: L2-squared distances, shape (nq, k), dtype float32.
                - indices: 0-based indices of neighbors, shape (nq, k), dtype int64.
        """
        # Set the search-time exploration factor. This is the main knob for the
        # speed-vs-accuracy trade-off at query time.
        self.index.hnsw.efSearch = self.ef_search
        
        # Ensure query vectors are in the correct format.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
        
        # Perform the search. Faiss automatically uses multiple CPU cores
        # for batch searches, which is highly efficient.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
