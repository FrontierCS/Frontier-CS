import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 100)
        self.ef_search = kwargs.get('ef_search', 40)
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.efConstruction = self.ef_construction
        self.index.max_codes = 1 << 32

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype('float32'))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.efSearch = self.ef_search
        D, I = self.index.search(xq.astype('float32'), k)
        return D, I
