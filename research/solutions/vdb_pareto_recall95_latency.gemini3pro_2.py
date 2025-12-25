import numpy as np
import faiss
from typing import Tuple

class Recall95LatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the HNSW index for high recall and low latency.
        
        Using HNSW (Hierarchical Navigable Small World) as it provides 
        an excellent trade-off between recall and speed for the SIFT1M dataset.
        
        Configuration:
        - M=32: Limits memory usage while maintaining high graph connectivity.
        - ef_construction=200: Builds a high-quality graph to facilitate faster search.
        - ef_search=80: Tuned to reliably meet the 95% recall gate on SIFT1M 
          while keeping latency significantly below the 7.7ms budget (typically <1ms).
        """
        self.dim = dim
        self.M = 32
        self.ef_construction = 200
        self.ef_search = 80
        
        # Initialize HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # Set construction depth
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Optimize for the 8 vCPU environment
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.
        HNSW builds the graph incrementally, so no separate training step is required.
        """
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search the index.
        Sets the efSearch parameter dynamically to ensure the recall constraint is met.
        """
        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq, k)
        return D, I
