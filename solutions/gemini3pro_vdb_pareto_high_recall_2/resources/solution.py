import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # High recall configuration for HNSW
        # M=64: Increases graph connectivity, improving recall at the cost of memory/build time
        # efConstruction=500: Builds a higher quality graph
        self.M = 64
        self.ef_construction = 500
        # efSearch=800: Large search depth to maximize recall within the 7.7ms latency budget
        self.ef_search = 800
        
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        # Ensure data is float32 and C-contiguous for Faiss
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        # Ensure query data is correct format
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq)
            
        # Set search parameter dynamically
        self.index.hnsw.efSearch = self.ef_search
        
        D, I = self.index.search(xq, k)
        return D, I
