import numpy as np
import faiss
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 40)
        self.ef_search = kwargs.get('ef_search', 16)
        self.index = None

    def add(self, xb: np.ndarray) -> None:
        if self.index is None:
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.efConstruction = self.ef_construction
            self.index.add(xb)
        else:
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is not None:
            self.index.efSearch = self.ef_search
        D, I = self.index.search(xq, k)
        return D.astype(np.float32), I.astype(np.int64)
