import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optimized for High Recall Tier with relaxed latency constraint (7.7ms).
        """
        self.dim = dim
        
        # HNSW Parameters
        # M=64: High connectivity for better graph navigation quality
        # ef_construction=256: Ensures high-quality graph construction
        # ef_search=384: Aggressive search depth to maximize recall. 
        # With 7.7ms budget and 8 vCPUs, we can afford this high depth.
        self.M = 64
        self.ef_construction = 256
        self.ef_search = 384
        
        # Initialize HNSW Flat index (HNSW graph + Flat storage)
        # Uses L2 (Euclidean) distance
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # FAISS requires float32 and C-contiguous arrays
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Ensure query vectors are in correct format
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq)
            
        # Set runtime search parameter
        # This controls the trade-off between speed and recall
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform batch search
        # FAISS automatically utilizes available CPU cores (OpenMP)
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
