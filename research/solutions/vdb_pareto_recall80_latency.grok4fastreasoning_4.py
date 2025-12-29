import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.index = faiss.IndexHNSWFlat(dim, 16)
        self.index.efConstruction = 100
        self.index.efSearch = 16

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        D, I = self.index.search(xq, k)
        return D, I