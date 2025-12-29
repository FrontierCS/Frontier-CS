import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Using HNSWFlat for high recall and low latency.
        """
        self.dim = dim
        
        # HNSW configuration
        # M=32 provides a good balance of graph connectivity and speed
        # ef_construction=256 ensures high quality graph structure
        M = 32
        self.ef_construction = 256
        
        # Search parameter
        # ef_search=160 is tuned to reliably exceed the 0.9914 recall baseline
        # while remaining well under the 5.775ms latency constraint on 8 vCPUs.
        self.ef_search = 160
        
        # Initialize HNSW Index with L2 metric
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Configure FAISS to use all available cores
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # FAISS requires C-contiguous arrays
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
            
        # Set search depth dynamically
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        D, I = self.index.search(xq, k)
        
        return D, I