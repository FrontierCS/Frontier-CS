import numpy as np
from typing import Tuple
import faiss

class Recall95Index:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # HNSW with Flat storage provides high recall with low latency
        # M=32 is a robust setting for SIFT1M
        self.index = faiss.IndexHNSWFlat(dim, 32)
        
        # High efConstruction improves graph quality, allowing faster search
        self.index.hnsw.efConstruction = 256
        
        # Ensure full utilization of available vCPUs
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        # FAISS requires C-contiguous float32 arrays
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        # efSearch=64 provides a safe margin for >95% recall on SIFT1M
        # while keeping latency well below the 7.7ms limit.
        # Ensure efSearch is at least k.
        self.index.hnsw.efSearch = max(64, k)
        
        return self.index.search(xq, k)