import numpy as np
import faiss
import os
from typing import Tuple

class BalancedTierIndex:
    """
    A Vector Database index for the Balanced Tier problem, optimized for maximum
    recall@1 under a strict latency constraint.

    This implementation uses Faiss's Hierarchical Navigable Small World (HNSW)
    graph-based index. HNSW is chosen for its excellent recall-speed trade-off,
    especially at the high-recall end of the spectrum, which is the primary goal
    of this problem.

    The strategy is to configure HNSW with parameters that build a high-quality
    graph (M, efConstruction) and then use a high search-time parameter (efSearch)
    to maximize recall, spending the available latency budget (up to 5.775ms).
    Parallelism is enabled to utilize all available CPU cores, which is critical
    for performance in a batch query environment.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters to override HNSW settings.
                      Supported keys: 'M', 'efConstruction', 'efSearch'.
        """
        self.dim = dim
        self.is_built = False

        # Utilize all available CPU cores for Faiss's parallel algorithms.
        try:
            num_threads = os.cpu_count()
            if num_threads:
                faiss.omp_set_num_threads(num_threads)
        except (AttributeError, NotImplementedError):
            pass

        # M: Number of neighbors per node. A larger M creates a denser graph,
        # improving recall at the cost of memory and build time. M=48 is a
        # strong choice for the SIFT1M dataset.
        self.M = kwargs.get('M', 48)

        # efConstruction: Controls graph quality during build. A higher value
        # leads to better recall but increases build time. 256 is a robust value.
        self.efConstruction = kwargs.get('efConstruction', 256)

        # efSearch: Controls search depth. Higher values increase recall and latency.
        # We choose a high value (384) to be aggressive on recall, aiming to use
        # the latency budget up to the 5.775ms limit.
        self.efSearch = kwargs.get('efSearch', 384)

        # Use IndexHNSWFlat to store full vectors for maximum accuracy.
        # METRIC_L2 corresponds to Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.efConstruction

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the HNSW index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Faiss requires C-contiguous float32 arrays.
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        if xb.shape[1] != self.dim:
            raise ValueError(f"Input vector dimension {xb.shape[1]} does not match index dimension {self.dim}")

        self.index.add(xb)
        self.is_built = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for the k nearest neighbors for each query vector.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: L2 distances, shape (nq, k), dtype float32.
                - indices: 0-based indices, shape (nq, k), dtype int64.
        """
        if not self.is_built:
            raise RuntimeError("Index has not been built. Call add() first.")

        # Set the search-time parameter.
        self.index.hnsw.efSearch = self.efSearch

        # Ensure query vectors are in the correct format for Faiss.
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        if xq.shape[1] != self.dim:
            raise ValueError(f"Query vector dimension {xq.shape[1]} does not match index dimension {self.dim}")

        distances, indices = self.index.search(xq, k)

        return distances, indices