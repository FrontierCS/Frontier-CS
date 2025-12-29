import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Using HNSW with tuned parameters for strict latency constraints.
        """
        self.dim = dim
        
        # HNSW configuration
        # M=32 provides a dense enough graph for high recall
        self.M = 32
        
        # ef_construction=200 builds a high-quality graph (improves recall per search op)
        # This only affects build time, not search latency
        self.ef_construction = 200
        
        # ef_search=45 is the critical parameter for latency.
        # With M=32, ef=45 typically achieves >90% recall on SIFT1M
        # while keeping latency well below the 2.31ms threshold on 8 vCPUs.
        self.ef_search = 45
        
        # Initialize the index
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Configure parallelism
        # Explicitly set to use all 8 available vCPUs for batch processing
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # xb is expected to be float32, which matches faiss requirements
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Set the search exploration depth dynamically
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform the search
        # xq: (nq, dim), output D: (nq, k), I: (nq, k)
        D, I = self.index.search(xq, k)
        
        return D, I