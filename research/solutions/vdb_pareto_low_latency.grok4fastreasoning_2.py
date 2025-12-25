import faiss
import numpy as np
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = kwargs.get('M', 12)
        ef_construction = kwargs.get('ef_construction', 80)
        ef_search = kwargs.get('ef_search', 32)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        self.index.nprobe = 1  # Not directly applicable, but for consistency

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype('float32'))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = 32  # Ensure low latency
        distances, indices = self.index.search(xq.astype('float32'), k)
        return distances, indices
