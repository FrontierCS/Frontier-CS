import numpy as np
import faiss
from typing import Tuple
import heapq

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW index optimized for recall with latency constraint.
        Parameters tuned for SIFT1M (1M vectors, 128D) to achieve
        recall > 0.9914 within 5.775ms.
        """
        self.dim = dim
        self.M = kwargs.get('M', 24)  # Increased connectivity for better recall
        self.ef_construction = kwargs.get('ef_construction', 300)  # High for construction quality
        self.ef_search = kwargs.get('ef_search', 200)  # High for recall, but watch latency
        self.store_n = 0
        
        # Create HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Enable efficient batch search
        self.index.verbose = False
    
    def add(self, xb: np.ndarray) -> None:
        """Add vectors to the index."""
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
        
        if self.store_n == 0:
            self.index.add(xb)
        else:
            # Add in chunks to avoid memory issues
            chunk_size = 100000
            for i in range(0, len(xb), chunk_size):
                chunk = xb[i:i + chunk_size]
                self.index.add(chunk)
        
        self.store_n += len(xb)
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        Uses optimized HNSW parameters for high recall within latency constraint.
        """
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
        
        # Dynamic efSearch adjustment based on query batch size
        # Larger batches can use higher ef for better recall
        if len(xq) >= 5000:
            self.index.hnsw.efSearch = 220  # Slightly higher for large batches
        else:
            self.index.hnsw.efSearch = self.ef_search
        
        # Set to use multiple threads for batch processing
        faiss.omp_set_num_threads(min(8, faiss.omp_get_max_threads()))
        
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)