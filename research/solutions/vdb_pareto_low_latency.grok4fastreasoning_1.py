import numpy as np
import faiss
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        m = kwargs.get('M', 16)
        ef_construction = kwargs.get('ef_construction', 100)
        self.index = faiss.IndexHNSWFlat(dim, m)
        self.index.efConstruction = ef_construction
        self.index.max_codes = 1 << 32  # Ensure 64-bit indices

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype('float32'))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        ef_search = kwargs.get('ef_search', 100) if 'kwargs' in locals() else 100
        self.index.efSearch = ef_search
        D, I = self.index.search(xq.astype('float32'), k)
        return D.astype('float32'), I.astype('int64')