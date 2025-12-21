import numpy as np
import faiss
from typing import Tuple

class BalancedIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # HNSW with M=32 is a robust configuration for 128-dim vectors,
        # providing a good balance of memory usage and graph navigability.
        self.M = 32
        
        # Higher ef_construction results in a higher quality graph, which allows
        # for better recall at the same search speed. Since construction time is
        # not scored (only limited to 1h), we maximize this.
        self.ef_construction = 256
        
        # ef_search determines the trade-off between recall and latency.
        # Baseline recall (0.9914) is achieved at ~3.85ms. 
        # The latency constraint is 5.775ms.
        # A value of 140 is tuned to reliably exceed the baseline recall 
        # while keeping latency safely under the 5.775ms limit on 8 vCPUs.
        self.ef_search = 140
        
        # Initialize HNSW Flat index (L2 distance)
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Ensure we utilize the available 8 vCPUs for batch processing
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        # Ensure input format compliance for FAISS
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        # Ensure query format compliance
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq)
            
        # Set search depth dynamically
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        return self.index.search(xq, k)
