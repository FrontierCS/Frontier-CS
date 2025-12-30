import numpy as np
import faiss
from typing import Tuple

class BalancedIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optimized for SIFT1M to achieve recall@1 > 0.9914 within 5.775ms latency.
        """
        self.dim = dim
        
        # HNSW parameters optimized for the problem constraints
        # M=32: Good balance of graph density and memory/speed
        # ef_construction=200: Ensures a high-quality graph structure
        # ef_search=128: Tuned to comfortably meet the 5.775ms constraint while aiming for >0.9914 recall
        self.M = kwargs.get('M', 32)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 128)
        
        # Environment has 8 vCPUs, ensure Faiss uses them
        faiss.omp_set_num_threads(8)
        
        # Initialize HNSW Flat index (L2 distance)
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure input is C-contiguous float32 as required by Faiss
        xb_internal = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb_internal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Ensure input is C-contiguous float32
        xq_internal = np.ascontiguousarray(xq, dtype=np.float32)
        
        # Set the search parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform batch search
        distances, indices = self.index.search(xq_internal, k)
        
        return distances, indices