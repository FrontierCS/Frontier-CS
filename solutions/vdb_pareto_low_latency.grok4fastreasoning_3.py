import numpy as np
import faiss
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        M = kwargs.get('M', 16)
        ef_construction = kwargs.get('ef_construction', 100)
        ef_search = kwargs.get('ef_search', 32)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype(np.float32))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq.astype(np.float32), k)
        return D, I
