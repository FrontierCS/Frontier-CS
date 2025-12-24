import numpy as np
from typing import Tuple
import faiss

class HNSWIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 64)
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.efConstruction = self.ef_construction
        self.id_map = np.arange(0, 0).astype(np.int64)  # Placeholder for indices

    def add(self, xb: np.ndarray) -> None:
        n = xb.shape[0]
        if len(self.id_map) == 0:
            self.id_map = np.arange(n, dtype=np.int64)
        else:
            self.id_map = np.concatenate([self.id_map, np.arange(len(self.id_map), len(self.id_map) + n, dtype=np.int64)])
        self.index.add_with_ids(xb.astype('float32'), self.id_map)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.efSearch = self.ef_search
        distances, indices = self.index.search(xq.astype('float32'), k)
        return distances, indices
