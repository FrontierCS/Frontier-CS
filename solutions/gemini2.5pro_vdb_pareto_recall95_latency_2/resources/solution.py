import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An efficient index for vector search optimized for high recall and low latency.
    This implementation uses FAISS's HNSW (Hierarchical Navigable Small Worlds) index,
    which is well-suited for high-recall scenarios on CPU.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initializes the index.

        Args:
            dim: The dimensionality of the vectors.
            **kwargs: Optional parameters for HNSW configuration.
                - M: Number of neighbors per node in the graph (default: 32).
                - efConstruction: Search beam width during index construction (default: 200).
                - efSearch: Search beam width during search (default: 100).
        """
        self.dim = dim

        # HNSW parameters are chosen to reliably exceed the 95% recall gate
        # while keeping latency low. These defaults provide a strong baseline.
        self.m = kwargs.get("M", 32)
        self.ef_construction = kwargs.get("efConstruction", 200)
        self.ef_search = kwargs.get("efSearch", 100)

        # Initialize the HNSW index. METRIC_L2 uses squared Euclidean distance,
        # which is faster for ranking and sufficient for this problem.
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        
        if hasattr(self.index, 'hnsw'):
            self.index.hnsw.efConstruction = self.ef_construction

        # The evaluation environment provides 8 vCPUs. We configure FAISS to
        # use all of them for parallelization, which is crucial for batch search performance.
        try:
            faiss.omp_set_num_threads(8)
        except AttributeError:
            # This may fail if FAISS is not compiled with OpenMP support,
            # but it is expected in the evaluation environment.
            pass

    def add(self, xb: np.ndarray) -> None:
        """
        Adds vectors to the index.

        Args:
            xb: A numpy array of shape (N, dim) and dtype float32 containing the vectors.
        """
        # FAISS requires input arrays to be C-contiguous and of type float32.
        # This call ensures the data is in the correct format, copying only if necessary.
        xb_processed = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb_processed)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Performs a k-nearest neighbor search.

        Args:
            xq: A numpy array of shape (nq, dim) and dtype float32 containing query vectors.
            k: The number of nearest neighbors to retrieve for each query.

        Returns:
            A tuple (distances, indices):
                - distances: A (nq, k) float32 array of L2-squared distances.
                - indices: A (nq, k) int64 array of indices of the nearest neighbors.
        """
        # Ensure the query vectors are in the correct C-contiguous float32 format.
        xq_processed = np.ascontiguousarray(xq, dtype=np.float32)

        # Set the search-time beam width. This is the primary knob for tuning
        # the trade-off between search speed and recall.
        if hasattr(self.index, 'hnsw'):
            self.index.hnsw.efSearch = self.ef_search
        
        # Execute the search. FAISS automatically parallelizes this across the configured threads.
        distances, indices = self.index.search(xq_processed, k)
        
        return distances, indices
