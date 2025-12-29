import numpy as np
from typing import Tuple
import faiss

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.index = faiss.IndexHNSWFlat(dim, 8)
        self.index.hnsw.efConstruction = 40
        self.index.hnsw.efSearch = 32

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype('float32'))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = xq.astype('float32')
        distances, indices = self.index.search(xq, k)
        return distances.astype('float32'), indices.astype('int64')