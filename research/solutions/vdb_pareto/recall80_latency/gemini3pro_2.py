import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for Recall80 Latency Tier.
        
        Implementation uses HNSW (Hierarchical Navigable Small World) with Flat storage.
        This provides the best trade-off for latency at the 80% recall constraint on CPU.
        
        Args:
            dim: Vector dimensionality (128 for SIFT1M)
            **kwargs: Optional parameters
        """
        self.dim = dim
        
        # Initialize HNSW index with Flat storage (exact distances within graph)
        # M=32 provides a dense enough graph for high recall with few hops
        self.index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_L2)
        
        # Set construction parameters high to build a high-quality graph
        # This moves computational cost to build time (allowed) to save search time
        self.index.hnsw.efConstruction = 200
        
        # Set search parameters for the Recall80 constraint
        # efSearch=20 is tuned for SIFT1M to achieve >80% recall (typically ~90%+)
        # while keeping latency extremely low (aiming for < 0.2ms)
        self.index.hnsw.efSearch = 20
        
        # Ensure the index utilizes all available vCPUs
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.
        
        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        self.index.add(xb)
        
        # Perform a warm-up search to initialize OpenMP thread pools and internal buffers
        # This prevents the first batch of measured queries from incurring initialization overhead
        if xb.shape[0] > 0:
            dummy_query = xb[:1].copy()
            self.index.search(dummy_query, 1)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        
        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors
            
        Returns:
            (distances, indices) tuple
        """
        # HNSW search is highly parallelized in Faiss
        # With efSearch=20, this should be very fast
        return self.index.search(xq, k)