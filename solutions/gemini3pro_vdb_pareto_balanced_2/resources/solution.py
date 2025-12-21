import numpy as np
import faiss
from typing import Tuple

class BalancedIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Optimization Strategy:
        - Use HNSW (Hierarchical Navigable Small World) for efficient approximate nearest neighbor search.
        - Set M=32: A robust balance for SIFT1M, providing high recall potential without excessive memory/compute.
        - Set efConstruction=500: Invest heavily in graph quality during build time (well within 1h timeout) 
          to improve search efficiency and recall.
        - Set efSearch=140: Tuned to maximize recall while safely staying under the 5.775ms latency constraint
          (which is 1.5x the baseline 3.85ms).
        - Explicitly enable 8 threads to utilize the full CPU capacity.
        """
        self.dim = dim
        self.M = 32
        self.ef_construction = 500
        self.ef_search = 140
        
        # Initialize HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # Configure construction parameters for maximum graph quality
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Ensure FAISS uses all available cores
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure data is contiguous and float32 for FAISS
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure query data is contiguous and float32
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set runtime search parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        # D: distances (squared L2), I: indices
        D, I = self.index.search(xq, k)
        
        return D, I
