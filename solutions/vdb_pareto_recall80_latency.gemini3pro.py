import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optimized for Recall@1 >= 0.80 and Latency <= 0.6ms on SIFT1M.
        """
        self.dim = dim
        # Set thread count to optimize for the 8 vCPU environment
        faiss.omp_set_num_threads(8)
        
        # HNSW Configuration
        # M: Number of connections per node. M=32 provides a robust graph 
        # that supports high recall with shallow searches.
        self.M = 32
        
        # ef_construction: Controls graph quality during build.
        self.ef_construction = 80
        
        # ef_search: Controls search depth/speed trade-off.
        # ef_search=16 with M=32 on SIFT1M typically yields Recall@1 > 0.90
        # with extremely low latency (approx 0.05ms - 0.15ms per query in batch).
        # This comfortably meets the >=0.80 recall gate and maximizes the latency score.
        self.ef_search = 16
        
        # Initialize HNSW Flat index (No quantization for max recall/speed efficiency)
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure input is float32 and contiguous for Faiss
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure input is float32 and contiguous for Faiss
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
        
        # Apply search-time parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        return distances, indices
