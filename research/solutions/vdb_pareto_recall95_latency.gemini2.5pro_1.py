import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters for HNSW:
                - M: Number of connections per node (default: 64).
                - ef_construction: Graph construction quality (default: 500).
                - ef_search: Search quality/speed trade-off (default: 48).
        """
        self.dim = dim
        
        self.M = kwargs.get('M', 64)
        self.ef_construction = kwargs.get('ef_construction', 500)
        self.ef_search = kwargs.get('ef_search', 48)

        # Use HNSWFlat for maximum accuracy without compression.
        # METRIC_L2 is the default and matches the problem's requirement.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Utilize all available CPU cores for parallelization.
        # The evaluation environment has 8 vCPUs.
        try:
            # Get available cores, fallback to 8 if not detectable.
            import os
            n_threads = len(os.sched_getaffinity(0))
        except (ImportError, AttributeError):
            n_threads = 8 # As specified in the environment description.
        faiss.omp_set_num_threads(n_threads)


    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Ensure data is C-contiguous for FAISS.
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        
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
            (distances, indices): Tuple of NumPy arrays.
                - distances: shape (nq, k), L2-squared distances.
                - indices: shape (nq, k), indices of the nearest neighbors.
        """
        # Set the search-time quality/speed trade-off parameter.
        self.index.hnsw.efSearch = self.ef_search
        
        # Ensure data is C-contiguous for FAISS.
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Perform the search. FAISS's HNSW search is parallelized.
        distances, indices = self.index.search(xq, k)
        
        # FAISS HNSW returns L2-squared distances for efficiency, which is
        # acceptable as per the problem specification ("L2 or L2-squared").
        return distances, indices
