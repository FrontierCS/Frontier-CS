import numpy as np
import faiss
from typing import Tuple

class HNSWSolution:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index using HNSW with Flat storage.
        
        Optimization strategy:
        - Use HNSW for robust recall/latency tradeoff.
        - M=32 provides a good graph connectivity for high recall.
        - efConstruction=200 ensures a high-quality graph structure (offline cost).
        - efSearch=64 is chosen to strictly meet the 2.31ms latency constraint.
          Typical latency for this config on 8 vCPUs is ~1.0-1.5ms for SIFT1M.
        """
        self.dim = dim
        
        # Optimize threading for the 8 vCPU environment
        faiss.omp_set_num_threads(8)
        
        # Initialize HNSW index with M=32
        self.index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_L2)
        
        # Set construction depth (affects build time, improves search speed/recall)
        self.index.hnsw.efConstruction = 200
        
        # Set search depth (critical for latency constraint)
        # Target latency < 2.31ms. efSearch=64 provides a safe margin.
        self.ef_search = 64

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.
        """
        # Faiss handles float32 arrays natively
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Set the search parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform batch search
        # D: distances, I: indices
        D, I = self.index.search(xq, k)
        
        return D, I
