import faiss
import numpy as np
from typing import Tuple

class VDBIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        nlist = 1000
        self.nprobe = 10
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, nlist, faiss.METRIC_L2)
        self.trained = False

    def add(self, xb: np.ndarray) -> None:
        if not self.trained:
            self.index.train(xb)
            self.trained = True
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.nprobe = self.nprobe
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)