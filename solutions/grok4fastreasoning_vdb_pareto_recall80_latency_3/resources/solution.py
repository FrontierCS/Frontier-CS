import numpy as np
import faiss
from typing import Tuple

class FastIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = kwargs.get('M', 16)
        self.index = faiss.IndexHNSWFlat(dim, M)
        ef_construction = kwargs.get('ef_construction', 100)
        self.index.hnsw.efConstruction = ef_construction
        ef_search = kwargs.get('ef_search', 32)
        self.index.hnsw.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype(np.float32))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        D, I = self.index.search(xq.astype(np.float32), k)
        return D.astype(np.float32), I.astype(np.int64)
