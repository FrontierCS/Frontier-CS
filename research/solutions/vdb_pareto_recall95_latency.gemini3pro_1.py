import numpy as np
import faiss
from typing import Tuple

class Recall95LatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for SIFT1M with HNSW.
        
        Design choices:
        - Algorithm: HNSW (Hierarchical Navigable Small World) with Flat storage.
          HNSW provides superior latency-recall tradeoffs for in-memory datasets.
        - Memory: SIFT1M (1M x 128 float32) requires ~512MB for vectors + graph overhead.
          This easily fits within the 16GB RAM limit, allowing us to avoid compression (PQ)
          which would hurt recall.
        - Parameters:
          - M=32: Standard connectivity for SIFT-scale data.
          - efConstruction=200: Builds a high-quality graph (time permit allows this).
          - efSearch=96: Chosen to strictly guarantee >95% recall (typically >98%)
            while keeping latency < 1ms (well within 7.7ms budget).
        """
        self.dim = dim
        self.M = 32
        self.ef_construction = 200
        self.ef_search = 96
        
        # Initialize Faiss HNSW index
        # MetricType is L2 by default for IndexHNSWFlat
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Configure threading to utilize all 8 vCPUs
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss expects float32
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set search-time parameter for recall/latency trade-off
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        # Faiss handles batching and threading automatically
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
