import numpy as np
import faiss
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = kwargs.get('M', 8)
        self.index = faiss.IndexHNSWFlat(dim, M)
        ef_construction = kwargs.get('ef_construction', 40)
        self.index.hnsw.efConstruction = ef_construction
        self.ef_search = kwargs.get('ef_search', 20)

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq, k)
        return D, I
