import numpy as np
import faiss
from typing import Tuple
import time

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall with relaxed latency.
        
        Parameters tuned for SIFT1M with 2x latency budget (7.7ms)
        """
        self.dim = dim
        
        # HNSW parameters optimized for high recall with 7.7ms budget
        # Higher M and ef_search for better recall
        self.M = kwargs.get('M', 48)  # Higher connectivity for better recall
        self.ef_construction = kwargs.get('ef_construction', 500)
        self.ef_search = kwargs.get('ef_search', 600)  # High for maximum recall
        
        # Initialize HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # For batch query optimization
        self.built = False
        
    def add(self, xb: np.ndarray) -> None:
        """Add vectors to the index."""
        if not self.built:
            # First batch - add directly
            self.index.add(xb)
        else:
            # Subsequent batches - use a temporary index and merge
            temp_index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
            temp_index.hnsw.efConstruction = self.ef_construction
            temp_index.hnsw.efSearch = self.ef_search
            temp_index.add(xb)
            
            # Get all vectors from both indices
            all_vectors = np.vstack([self.index.reconstruct_n(0, self.index.ntotal),
                                     temp_index.reconstruct_n(0, temp_index.ntotal)])
            
            # Rebuild the index
            self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search
            self.index.add(all_vectors)
        
        self.built = True
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Search for k nearest neighbors with optimized batch processing."""
        # Dynamic ef_search adjustment based on batch size
        # Smaller batches can use higher ef_search
        nq = xq.shape[0]
        
        # Optimize for the specific test condition (10k queries)
        # Use high ef_search for maximum recall within latency budget
        self.index.hnsw.efSearch = min(800, max(400, self.ef_search))
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)