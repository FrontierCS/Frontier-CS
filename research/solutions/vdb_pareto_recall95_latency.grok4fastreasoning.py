import numpy as np
from typing import Tuple
import faiss

class VDBIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = kwargs.get('M', 32)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 200)

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq, k)
        return D, I
