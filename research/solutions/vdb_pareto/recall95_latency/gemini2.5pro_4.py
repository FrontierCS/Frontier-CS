import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        This implementation uses Faiss's HNSW (Hierarchical Navigable Small World)
        index, which is optimized for high-recall and low-latency search on CPUs.
        Parameters are tuned to meet the Recall@1 >= 0.95 constraint for the
        SIFT1M dataset while minimizing query latency.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters for HNSW.
                - M: Number of neighbors per node (default: 32).
                - ef_construction: Build-time search depth (default: 200).
                - ef_search: Query-time search depth (default: 50).
        """
        self.dim = dim

        # HNSW parameters chosen for a strong recall/latency trade-off.
        # M=32 provides a good graph structure.
        # ef_construction=200 ensures a high-quality index build.
        # ef_search=50 is selected to reliably exceed 95% recall while
        # being low enough to provide a significant latency improvement
        # over more conservative (higher recall) settings.
        m = kwargs.get('M', 32)
        ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 50)

        # Initialize the HNSW index with L2 distance. Faiss uses squared L2
        # for this metric, which is acceptable per the problem statement.
        self.index = faiss.IndexHNSWFlat(self.dim, m, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Faiss requires input arrays to be of dtype float32.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: L2-squared distances, shape (nq, k).
                - indices: Vector indices, shape (nq, k).
        """
        # Ensure query vectors are float32.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time parameter efSearch. This is the crucial knob
        # for tuning the speed vs. accuracy trade-off at query time.
        self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, k)

        return distances, indices