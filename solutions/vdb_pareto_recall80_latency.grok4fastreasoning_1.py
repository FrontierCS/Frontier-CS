import faiss
import numpy as np
from typing import Tuple

class VDBLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        nlist = 1000
        m = 8
        bits = 8
        self.nprobe = 10
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFPQ(self.quantizer, dim, nlist, m, bits)
        self.trained = False

    def add(self, xb: np.ndarray) -> None:
        if not self.trained:
            self.index.train(xb)
            self.trained = True
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.nprobe = self.nprobe
        D, I = self.index.search(xq, k)
        return D, I
