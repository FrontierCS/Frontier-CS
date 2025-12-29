import faiss
import numpy as np
from typing import Tuple

class LatencyOptimizedIndex:
    def __init__(self, dim: int, **kwargs):
        quantizer = faiss.IndexFlatL2(dim)
        nlist = kwargs.get('nlist', 1000)
        self.index = faiss.IndexIVFFlat(quantizer, dim, nlist)
        self.trained = False

    def add(self, xb: np.ndarray) -> None:
        if not self.trained:
            self.index.train(xb)
            self.trained = True
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.nprobe = 50
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)