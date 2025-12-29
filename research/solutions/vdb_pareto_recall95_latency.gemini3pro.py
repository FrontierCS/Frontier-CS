import numpy as np
import faiss
from typing import Tuple

class Recall95Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Uses HNSW (Hierarchical Navigable Small World) graph which offers 
        state-of-the-art performance for high-recall, low-latency search on CPU.
        """
        self.dim = dim
        # Explicitly set the number of threads to utilize the 8 vCPUs available
        faiss.omp_set_num_threads(8)
        
        # HNSW Hyperparameters
        # M: Number of neighbors per node in the graph. 
        # M=32 is a robust sweet spot for SIFT1M (128d), balancing graph density and traversal speed.
        self.M = kwargs.get('M', 32)
        
        # efConstruction: Controls the depth of the search during index construction.
        # Higher values lead to a higher quality graph (better recall/speed tradeoff later)
        # at the cost of slower build time. Given the 1h timeout, we can afford 200.
        self.ef_construction = kwargs.get('ef_construction', 200)
        
        # efSearch: Controls the depth of the search during queries.
        # This is the primary knob for Recall vs Latency.
        # For SIFT1M with HNSW32, ef=64 typically yields recall > 0.98,
        # providing a safe margin above the 0.95 requirement while keeping latency < 1ms.
        self.ef_search = kwargs.get('ef_search', 64)
        
        # Initialize Faiss HNSW Index
        # We use IndexHNSWFlat which stores the full vectors for precise distance calculation
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss requires C-contiguous float32 arrays
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Ensure query vectors are in the correct format
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Ensure efSearch is set to our target value before searching
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform batch search
        # Faiss handles batching and threading internally
        D, I = self.index.search(xq, k)
        
        return D, I