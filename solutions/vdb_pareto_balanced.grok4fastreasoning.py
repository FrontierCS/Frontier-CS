import numpy as np
from typing import Tuple
import faiss

class VectorIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = kwargs.get('M', 16)
        self.index = faiss.IndexHNSWFlat(dim, M)
        ef_construction = kwargs.get('ef_construction', 200)
        self.index.hnsw.efConstruction = ef_construction
        ef_search = kwargs.get('ef_search', 200)
        self.index.hnsw.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)
