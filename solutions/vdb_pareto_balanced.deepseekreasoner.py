import numpy as np
import faiss
import time
from typing import Tuple

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for recall while meeting latency constraint.
        Parameters tuned for SIFT1M (1M vectors, 128 dim) on 8 vCPU CPU-only environment.
        """
        self.dim = dim
        
        # HNSW parameters optimized for recall@1 > 0.9914 while meeting 5.775ms latency
        # Using conservative settings to maximize recall
        M = kwargs.get('M', 32)  # Higher M for better recall (16 is baseline, 32 for better connectivity)
        ef_construction = kwargs.get('ef_construction', 400)  # High for maximum recall
        ef_search = kwargs.get('ef_search', 256)  # High for maximum recall
        
        # Create HNSW index
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        
        # Store for batch optimization
        self.xb = None
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        Optimized for SIFT1M scale (1M vectors).
        """
        self.xb = xb if self.xb is None else np.vstack([self.xb, xb])
        self.index.add(xb)
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        Optimized for batch queries (10K queries) with focus on recall.
        """
        # Set efSearch for this query batch
        # Conservative value to maximize recall
        self.index.hnsw.efSearch = 256
        
        # Perform search
        D, I = self.index.search(xq, k)
        
        # Convert to required dtypes
        return D.astype(np.float32), I.astype(np.int64)
