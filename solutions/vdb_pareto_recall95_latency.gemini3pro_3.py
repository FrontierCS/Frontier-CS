import numpy as np
import faiss
from typing import Tuple

class Recall95Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Implementation uses Faiss HNSW (Hierarchical Navigable Small World) index.
        HNSW is chosen for its superior performance in high-recall regimes with 
        low latency constraints.
        
        Configuration:
        - M=48: Higher connectivity in the graph to ensure robust navigation 
          and high recall (R@1 >= 0.95).
        - efConstruction=200: High quality graph construction.
        - efSearch=128: Sufficiently large search buffer to guarantee recall 
          while remaining extremely fast (< 2ms typically) on SIFT1M.
        """
        self.dim = dim
        
        # Hyperparameters
        self.M = 48
        self.efConstruction = 200
        self.efSearch = 128
        
        # Initialize Faiss IndexHNSWFlat
        # Uses L2 distance (squared L2 by default in Faiss, which is allowed)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        
        # Set construction parameter
        self.index.hnsw.efConstruction = self.efConstruction
        
        # Configure threading for the 8 vCPU environment to maximize batch search throughput
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure input is float32 (required by Faiss)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Ensure input is float32
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set search parameter
        # Ensure efSearch is at least k to prevent warnings/errors
        self.index.hnsw.efSearch = max(self.efSearch, k)
        
        # Perform search
        # Returns distances (L2 squared) and indices
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
