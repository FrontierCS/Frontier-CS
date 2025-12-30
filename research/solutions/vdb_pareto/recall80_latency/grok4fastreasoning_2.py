import numpy as np
from typing import Tuple
import faiss

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = 16
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = 40
        self.index.hnsw.efSearch = 16

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        D, I = self.index.search(xq, k)
        return D.astype(np.float32), I.astype(np.int64)