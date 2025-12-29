import numpy as np
import faiss
from typing import Tuple

class VDBIndex:
    def __init__(self, dim: int, **kwargs):
        M = kwargs.get('M', 32)
        ef_construction = kwargs.get('ef_construction', 400)
        ef_search = kwargs.get('ef_search', 400)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.efConstruction = ef_construction
        self.index.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        D, I = self.index.search(xq, k)
        return D.astype(np.float32), I.astype(np.int64)