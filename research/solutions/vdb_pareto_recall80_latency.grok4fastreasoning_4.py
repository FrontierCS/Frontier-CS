import faiss
import numpy as np
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        nlist = 1024
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IVFFlat(self.quantizer, dim, nlist)
        self.index.nprobe = 10
        self.trained = False

    def add(self, xb: np.ndarray) -> None:
        if not self.trained:
            self.index.train(xb)
            self.trained = True
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        D, I = self.index.search(xq, k)
        return D.astype(np.float32), I.astype(np.int64)
