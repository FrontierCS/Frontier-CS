import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optimized for Recall@1 >= 0.80 and Latency < 0.6ms on SIFT1M.
        """
        self.dim = dim
        
        # Set number of threads to utilize the 8 vCPUs available in the environment
        faiss.omp_set_num_threads(8)
        
        # Use HNSW (Hierarchical Navigable Small World) for fast ANN search
        # M=32 provides a robust graph structure for 128-dim vectors
        self.index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_L2)
        
        # efConstruction=80 provides a good balance of build time and graph quality
        self.index.hnsw.efConstruction = 80
        
        # Search parameter tuning:
        # efSearch controls the trade-off between recall and latency.
        # For SIFT1M (M=32), efSearch=18 typically achieves Recall@1 ~0.85-0.90,
        # which safely clears the 0.80 gate while remaining extremely fast (<0.2ms).
        self.ef_search = 18

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        HNSW builds the graph incrementally, so no separate training step is required.
        """
        # Ensure input is float32 (Faiss requirement)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure query is float32
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set search-time parameter
        # Faiss internally ensures ef >= k, but we set it explicitly to our tuned value
        self.index.hnsw.efSearch = max(self.ef_search, k)
        
        # Perform search (OpenMP parallelized across queries)
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
