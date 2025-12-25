import numpy as np
import faiss
from typing import Tuple

class VDBIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = kwargs.get('M', 32)
        ef_construction = kwargs.get('ef_construction', 100)
        self.ef_search = kwargs.get('ef_search', 100)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)
