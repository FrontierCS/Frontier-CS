import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.M = kwargs.get("M", 64)
        self.efConstruction = kwargs.get("efConstruction", 400)
        self.efSearch = kwargs.get("efSearch", kwargs.get("ef_search", 768))

        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.efConstruction
        
        self.is_built = False

    def add(self, xb: np.ndarray) -> None:
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        elif xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        self.index.add(xb)
        self.is_built = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_built:
            nq = xq.shape[0]
            distances = np.full((nq, k), np.inf, dtype=np.float32)
            indices = np.full((nq, k), -1, dtype=np.int64)
            return distances, indices

        self.index.hnsw.efSearch = self.efSearch
        
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        elif xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
