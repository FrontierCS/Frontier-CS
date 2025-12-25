import numpy as np
import faiss
from typing import Tuple

class VDBIndex:
    def __init__(self, dim: int, **kwargs):
        M = 32
        ef_construction = 200
        self.ef_search = 128
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.train_type = faiss.HNSWStats(0)

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype('float32'))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq.astype('float32'), k)
        return D, I
