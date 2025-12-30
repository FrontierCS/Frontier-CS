import numpy as np
import faiss
from typing import Tuple

class VectorIndexHighRecall:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = 32
        self.ef_construction = 200
        self.ef_search = 400
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq, k)
        return D, I.astype(np.int64)