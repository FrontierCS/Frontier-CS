import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Configuration optimized for Recall@1 > 0.9914 within 7.7ms latency budget.
        """
        self.dim = dim
        
        # HNSW Configuration
        # M=64: High connectivity graph for maximizing recall
        # ef_construction=256: Deeper search during build for better graph quality
        # ef_search=300: Aggressive search depth allowed by relaxed latency constraints
        self.M = 64
        self.ef_construction = 256
        self.ef_search = 300
        
        # Initialize Faiss HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Optimize threading for the 8 vCPU environment
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure data is float32 and C-contiguous for Faiss
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure query data is float32 and C-contiguous
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
            
        # Set search depth parameter dynamically
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances, indices