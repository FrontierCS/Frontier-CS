import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Configuration optimized for SIFT1M on CPU to maximize Recall@1 
        while satisfying the 5.775ms latency constraint.
        """
        # Ensure we use all available vCPUs
        faiss.omp_set_num_threads(8)
        
        self.dim = dim
        
        # HNSW Configuration
        # M=48: Higher than standard (32) to improve graph connectivity and recall
        M = 48
        
        # Create HNSW index with L2 metric (Exact distances for maximum precision)
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        
        # Construction Parameters
        # efConstruction=200: Builds a high-quality graph structure
        # This takes longer to build but improves search efficiency/recall
        self.index.hnsw.efConstruction = 200
        
        # Search Parameters
        # efSearch=128: empirically selected to reliably exceed 0.9914 recall
        # while keeping batch latency well below 5.775ms on 8 vCPUs.
        self.ef_search = 128

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure input is float32 (FAISS requirement)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Ensure query is float32
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set the search depth for this query batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        # Returns (distances, indices)
        return self.index.search(xq, k)