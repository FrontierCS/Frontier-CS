import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optimized for low latency (constraint < 2.31ms) on SIFT1M.
        """
        self.dim = dim
        
        # HNSW Parameters
        # M=16 is reduced from standard 32 to improve search speed per hop
        self.M = 16 
        
        # efConstruction determines graph quality. Higher values (e.g. 100-200) 
        # improve recall potential without affecting search latency.
        self.ef_construction = 128
        
        # efSearch is the critical runtime knob.
        # Based on baseline (3.85ms) vs limit (2.31ms), we need aggressive speedup.
        # efSearch=50 combined with M=16 provides a safe margin (target ~1.8ms)
        # while maintaining recall typically > 0.95.
        self.ef_search = 50
        
        # Ensure FAISS uses all available vCPUs (Environment has 8)
        faiss.omp_set_num_threads(8)
        
        # Initialize HNSW Flat index
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure correct data type and memory layout for FAISS
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure correct data type and memory layout
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq)
            
        # Set runtime search parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances, indices