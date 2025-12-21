import faiss
import numpy as np
from typing import Tuple

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        M = 64
        ef_construction = 400
        ef_search = 800
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq, k)
        return D.astype(np.float32), I.astype(np.int64)
