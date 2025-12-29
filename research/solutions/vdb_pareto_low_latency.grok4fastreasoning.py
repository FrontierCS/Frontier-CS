import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 100)
        self.ef_search = kwargs.get('ef_search', 50)
        self.index = None

    def add(self, xb: np.ndarray) -> None:
        xb = xb.astype('float32')
        if self.index is None:
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.add(xb)
        else:
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = xq.astype('float32')
        self.index.hnsw.efSearch = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)