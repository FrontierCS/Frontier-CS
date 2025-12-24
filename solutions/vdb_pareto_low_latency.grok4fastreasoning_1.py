import faiss
import numpy as np
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        m = 8
        self.index = faiss.IndexHNSWFlat(dim, m)
        self.index.hnsw.efConstruction = 50
        self.index.hnsw.efSearch = 20
        self.index_additive = 0

    def add(self, xb: np.ndarray) -> None:
        xb = xb.astype('float32')
        n = xb.shape[0]
        self.index.add_with_ids(xb, np.arange(self.index_additive, self.index_additive + n, dtype=np.int64))
        self.index_additive += n

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = xq.astype('float32')
        distances, indices = self.index.search(xq, k)
        return distances.astype('float32'), indices.astype('int64')
