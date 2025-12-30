import numpy as np
import faiss
from typing import Tuple

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.index = None
        
        # HNSW parameters optimized for recall with latency constraint
        self.M = kwargs.get('M', 24)  # Increased from 16 for better recall
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 128)  # Increased for higher recall
        
    def add(self, xb: np.ndarray) -> None:
        if self.index is None:
            # Create HNSW index with L2 distance
            self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search
        
        # Add vectors to the index
        self.index.add(xb)
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        # Set search parameters for batch queries
        if hasattr(self.index.hnsw, 'efSearch'):
            self.index.hnsw.efSearch = self.ef_search
        
        # Search for k nearest neighbors
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)