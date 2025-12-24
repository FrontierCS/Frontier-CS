import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An efficient index for vector similarity search, optimized for high recall
    under a strict latency constraint. It uses Faiss's HNSW implementation.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        The parameters M, ef_construction, and ef_search are tuned to maximize
        recall@1 for the SIFT1M dataset while staying within the 5.775ms
        latency limit on the specified evaluation hardware.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters to override the tuned defaults.
                      Expected keys: 'M', 'ef_construction', 'ef_search'.
        """
        self.dim = dim
        
        # --- Tuned HNSW parameters ---
        # M: Graph connectivity. Higher M improves recall but uses more memory/build time.
        #    48 is a robust choice for good graph structure on SIFT1M.
        self.M = kwargs.get("M", 48)
        
        # efConstruction: Build-time quality factor. Higher is better but slower.
        #                 Build time is a one-off cost, so we can be generous.
        self.ef_construction = kwargs.get("ef_construction", 200)
        
        # efSearch: Search-time quality factor. This is the primary knob for the
        #           recall/latency trade-off. 192 is an aggressive value chosen
        #           to fully utilize the 5.775ms latency budget to maximize recall.
        self.ef_search = kwargs.get("ef_search", 192)

        # Initialize the Faiss HNSW index with the L2 (Euclidean) metric.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.

        Args:
            xb: A numpy array of shape (N, dim) and dtype float32 containing the
                vectors to be added.
        """
        # Faiss requires C-contiguous float32 arrays for optimal performance.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for the k nearest neighbors for each query vector.

        Args:
            xq: A numpy array of shape (nq, dim) and dtype float32 containing
                the query vectors.
            k: The number of nearest neighbors to retrieve.

        Returns:
            A tuple (distances, indices):
                - distances: (nq, k) float32 array of squared L2 distances.
                - indices: (nq, k) int64 array of vector indices.
        """
        if self.index.ntotal == 0:
            # Return empty/sentinel results if the index is not populated.
            distances = np.full((xq.shape[0], k), -1, dtype=np.float32)
            indices = np.full((xq.shape[0], k), -1, dtype=np.int64)
            return distances, indices

        # Set the search-time parameter before querying.
        self.index.hnsw.efSearch = self.ef_search

        # Ensure query vectors are in the correct format for Faiss.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
        
        # Perform the search. Faiss HNSW with METRIC_L2 returns squared L2 distances,
        # which is permitted by the problem statement ("L2 or L2-squared").
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
