import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        We use HNSW with Flat storage to ensure high recall.
        
        Configuration:
        - M=64: Creates a dense graph, improving recall at the cost of memory/build time.
        - efConstruction=256: Improves graph quality during construction.
        - efSearch=320: High search depth to maximize recall while staying within the 5.775ms latency limit.
        """
        self.dim = dim
        # HNSWFlat stores raw vectors and builds an HNSW graph
        self.index = faiss.IndexHNSWFlat(dim, 64, faiss.METRIC_L2)
        
        # Set construction parameters
        self.index.hnsw.efConstruction = 256
        
        # Set default search parameters
        self.ef_search = 320
        
        # Configure for the evaluation environment (8 vCPUs)
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure data is contiguous and float32 as required by Faiss
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure data is contiguous and float32
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        # Adjust efSearch to be at least k, maximizing recall
        self.index.hnsw.efSearch = max(self.ef_search, k)
        
        # Perform batch search
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
