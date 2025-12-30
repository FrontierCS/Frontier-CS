import numpy as np
from typing import Tuple
import faiss

class HNSWIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = kwargs.get('M', 32)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 50)
        self.index = faiss.IndexHNSWFlat(dim, int(self.M))
        self.index.hnsw.efConstruction = int(self.ef_construction)

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype(np.float32))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = int(self.ef_search)
        Dsq, I = self.index.search(xq.astype(np.float32), k)
        D = np.sqrt(Dsq).astype(np.float32)
        I = I.astype(np.int64)
        return D, I