import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Using HNSW graph-based index for optimal recall/latency balance.
        """
        self.dim = dim
        
        # HNSW Parameters optimized for SIFT1M on CPU
        # M=32 provides a dense enough graph for high recall
        self.M = 32
        
        # ef_construction=200 ensures high graph quality during build
        # (Does not affect search latency)
        self.ef_construction = 200
        
        # ef_search determines the search budget.
        # Tuned to satisfy the strict <2.31ms constraint while maximizing recall.
        # With 8 vCPUs and batching, ef_search=80 is safely within limits
        # and typically yields recall@1 > 0.98.
        self.ef_search = 80
        
        # Initialize Faiss HNSW Flat index (L2 distance)
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Ensure Faiss uses all available cores (8 vCPUs)
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss handles adding vectors efficiently
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Set the search-time parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform batch search
        D, I = self.index.search(xq, k)
        
        return D, I
