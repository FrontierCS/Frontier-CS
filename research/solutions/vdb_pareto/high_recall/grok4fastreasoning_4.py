import numpy as np
import faiss
from typing import Tuple

class ExactIndex:
    def __init__(self, dim: int, **kwargs):
        self.index = faiss.IndexFlatL2(dim)

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        D, I = self.index.search(xq, k)
        return D, I