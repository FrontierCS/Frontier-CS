import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # HNSW configuration
        # M=32 is a standard balance for SIFT1M.
        # ef_construction=500 ensures a high-quality graph structure (slower build, better search).
        # ef_search=144 is tuned to guarantee recall > 0.9914 while remaining within the 5.775ms limit.
        self.M = 32
        self.ef_construction = 500
        self.ef_search = 144
        
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        return self.index.search(xq, k)