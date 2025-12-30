import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A Vector Database Index optimized for high recall, leveraging the FAISS library's
    HNSW (Hierarchical Navigable Small World) implementation.

    This index is configured with parameters that prioritize search accuracy (recall)
    over speed, making it suitable for scenarios with a relaxed latency constraint.
    It uses IndexHNSWFlat, which stores full-precision vectors to avoid any loss
    of accuracy from compression techniques like Product Quantization.

    The key tuning parameters are:
    - M: The number of bi-directional links created for every new element during
      construction. Higher M leads to a more robust graph and higher recall.
    - efConstruction: Controls the quality of the graph construction. A higher
      value leads to a better index and higher potential recall.
    - efSearch: Controls the depth of the search at query time. This is the
      primary knob for trading off speed for accuracy. A very high value is used
      here to maximize recall within the given latency budget.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters for HNSW.
                - M (int): Number of neighbors for HNSW graph nodes. Default: 64.
                - ef_construction (int): HNSW construction parameter. Default: 512.
                - ef_search (int): HNSW search parameter. Default: 1024.
        """
        self.dim = dim
        # Parameters tuned for high recall, taking advantage of the relaxed latency.
        # These values are aggressive to create a high-quality graph and perform a thorough search.
        self.m = int(kwargs.get("M", 64))
        self.ef_construction = int(kwargs.get("ef_construction", 512))
        self.ef_search = int(kwargs.get("ef_search", 1024))

        # Use IndexHNSWFlat for maximum recall. It does not use compression,
        # storing the full vectors. METRIC_L2 is the specified distance metric.
        # Faiss HNSW returns squared L2 distances, which is acceptable.
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        
        # Set the construction-time parameter.
        self.index.hnsw.efConstruction = self.ef_construction
        
        self.is_built = False

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Input array xb must have shape (N, {self.dim})")
        
        # FAISS requires float32 input.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        # HNSWFlat does not require a separate training step.
        # Adding vectors builds the graph structure.
        self.index.add(xb)
        self.is_built = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances.
                - indices: shape (nq, k), dtype int64, indices into base vectors.
        """
        if not self.is_built:
            raise RuntimeError("Index is not built yet. Call add() first.")
        
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Input array xq must have shape (nq, {self.dim})")
            
        if k <= 0:
            raise ValueError("k must be a positive integer.")

        # FAISS requires float32 input.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time parameter. This is the main lever for the
        # speed-recall tradeoff. A high value is chosen for this high-recall tier.
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform the search. The number of threads is controlled by OMP_NUM_THREADS
        # environment variable, and FAISS will use multiple cores by default.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices