import faiss
import numpy as np
from typing import Tuple

class MyIndex:
    def __init__(self, dim: int, **kwargs):
        M = kwargs.get('M', 16)
        ef_construction = kwargs.get('ef_construction', 100)
        ef_search = kwargs.get('ef_search', 100)
        self.dim = dim
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.efConstruction = ef_construction
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype(np.float32))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.efSearch = self.ef_search
        D, I = self.index.search(xq.astype(np.float32), k)
        return D, I