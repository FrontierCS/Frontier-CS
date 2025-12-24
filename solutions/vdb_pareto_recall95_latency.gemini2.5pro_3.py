import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    """
    An efficient VDB index implementation using Faiss's HNSWFlat.

    This index is optimized for the Recall95 Latency tier, aiming to
    achieve at least 95% recall@1 while minimizing query latency. It
    builds a high-quality HNSW graph (controlled by M and ef_construction)
    which allows for a faster, less exhaustive search (controlled by ef_search)
    at query time. This strikes a balance that favors low latency once the
    high recall gate is passed.

    The hyperparameters (M, ef_construction, ef_search) are chosen based on
    common practices for the SIFT1M dataset and are tuned to aggressively
    reduce latency by aiming for a recall just above the 95% threshold,
    thereby maximizing the potential score.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW: M, ef_construction, ef_search
        """
        self.dim = dim

        # Hyperparameters chosen for a high-quality index to enable low-latency search.
        # M: Number of neighbors per node in the HNSW graph.
        self.M = int(kwargs.get("M", 48))
        # ef_construction: Build-time search depth for graph construction.
        self.ef_construction = int(kwargs.get("ef_construction", 400))
        # ef_search: Query-time search depth. This is the key parameter tuned
        # to trade excess recall for lower latency.
        self.ef_search = int(kwargs.get("ef_search", 90))

        # Using HNSWFlat for maximum accuracy per visited node, as memory is not a
        # primary constraint. METRIC_L2 computes squared Euclidean distance, which
        # is faster and sufficient for nearest neighbor search.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Note: Faiss compiled with OpenMP will automatically use all available
        # CPU cores for build and search, which is optimal for this environment.
        # No explicit thread management is necessary.

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. For HNSW, this builds the graph structure.

        Args:
            xb: Base vectors, shape (N, dim), dtype must be convertible to float32.
        """
        # Faiss requires float32 data for its computations.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype must be convertible to float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances.
                - indices: shape (nq, k), dtype int64, 0-based indices of the neighbors.
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time exploration factor. This controls the trade-off
        # between search speed and accuracy.
        self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, k)

        return distances, indices
