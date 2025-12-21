import numpy as np
import faiss
from typing import Tuple

class LowLatencyHNSW:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optimized for strict low latency (< 2.31ms) on CPU.
        """
        self.dim = dim
        # M=24 reduces graph connectivity vs standard M=32, improving speed per hop
        # This is a key trade-off for the strict latency constraint (2.31ms)
        self.M = 24
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # Maximize graph quality during construction since build time isn't the primary constraint
        # High efConstruction allows better recall at lower efSearch values
        self.index.hnsw.efConstruction = 200
        
        # Utilize all 8 vCPUs for batch processing
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure data is contiguous C-order float32 for Faiss
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # efSearch controls the search depth (recall vs latency trade-off)
        # Target latency: < 2.31ms. Baseline (M=32, ef~64) is ~3.85ms.
        # Setting efSearch=42 with M=24 provides a safety margin (est. ~1.8-2.0ms)
        # while maintaining high recall (>0.94) within the allowed window.
        search_ef = max(k, 42)
        self.index.hnsw.efSearch = search_ef
        
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
            
        return self.index.search(xq, k)
