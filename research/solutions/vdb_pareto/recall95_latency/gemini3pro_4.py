import numpy as np
import faiss
from typing import Tuple

class Recall95Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index using HNSW for high recall and low latency.
        
        Algorithm choice: HNSW (Hierarchical Navigable Small World)
        Rationale:
        - HNSW is state-of-the-art for high-recall in-memory search.
        - SIFT1M (1M vectors) fits easily in memory (approx 300-600MB with graph overhead).
        - Latency budget (7.7ms) is generous for HNSW, which typically achieves sub-millisecond 
          latency for Recall@1 > 0.95 on this dataset.
        
        Parameters:
        - M=32: Good balance of graph connectivity and memory/speed.
        - ef_construction=200: Ensures a high-quality graph structure (slower build, faster search).
        - ef_search=64: Tuned to strictly meet the 0.95 recall gate (typically achieves ~0.99)
          while keeping latency minimized.
        """
        self.dim = dim
        self.M = 32
        self.ef_construction = 200
        self.ef_search = 64
        
        # IndexHNSWFlat uses full vectors (no compression) and L2 distance
        # This ensures maximum precision to meet the recall constraint
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # Set construction depth
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Configure threading for the evaluation environment (8 vCPUs)
        # Batch queries benefit from parallel execution
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.
        """
        # Faiss requires C-contiguous arrays for optimal performance
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
            
        # Set efSearch dynamically to ensure it's at least k
        # ef_search=64 is the baseline for high recall
        self.index.hnsw.efSearch = max(self.ef_search, k)
        
        D, I = self.index.search(xq, k)
        return D, I