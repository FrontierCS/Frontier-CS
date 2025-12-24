import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An high-recall vector database index using FAISS's HNSW implementation.

    This index is optimized for the High Recall Tier, where the goal is to
    maximize recall@1 under a relaxed latency constraint (7.7ms). It uses
    HNSW (Hierarchical Navigable Small Worlds), a graph-based ANN algorithm
    known for its excellent speed-recall trade-offs.

    To achieve high recall, this implementation uses:
    1.  `IndexHNSWFlat`: Stores full, uncompressed vectors to avoid any
        quantization error, maximizing accuracy.
    2.  Aggressive HNSW parameters:
        -   `M=64`: A high number of neighbors per node, creating a dense and
            high-quality navigation graph.
        -   `efConstruction=400`: A high search depth during index build time,
            ensuring the graph quality is excellent.
        -   `efSearch=800`: A very high search depth at query time. This is the
            primary mechanism to trade increased latency for higher recall,
            leveraging the generous 7.7ms time budget.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW
                - M: Number of neighbors for HNSW graph (default: 64)
                - ef_construction: Build-time search depth (default: 400)
                - ef_search: Query-time search depth (default: 800)
        """
        self.dim = dim
        
        # Parameters for HNSW, optimized for high recall
        self.m = int(kwargs.get("M", 64))
        self.ef_construction = int(kwargs.get("ef_construction", 400))
        self.ef_search = int(kwargs.get("ef_search", 800))

        # Use IndexHNSWFlat for maximum accuracy (no compression)
        # METRIC_L2 is Euclidean distance
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        
        # Set the construction-time parameter
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
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
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)

        # Set the search-time parameter. This is the crucial knob for the
        # speed-recall tradeoff. A high value is used to leverage the relaxed
        # latency constraint.
        self.index.hnsw.efSearch = self.ef_search
        
        # FAISS HNSW returns squared L2 distances by default for efficiency.
        # This is acceptable as per the problem description.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
