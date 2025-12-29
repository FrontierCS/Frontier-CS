import faiss
import numpy as np
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        nlist = kwargs.get('nlist', 1000)
        self.nprobe = kwargs.get('nprobe', 8)
        quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(quantizer, dim, nlist)
        self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        if not self.index.is_trained:
            self.index.train(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        D, I = self.index.search(xq, k)
        return D, I