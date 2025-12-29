import numpy as np
import faiss
from typing import Tuple

class Recall95LatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW index optimized for high recall (≥95%) with latency focus.
        Parameters tuned for SIFT1M with 128 dimensions.
        """
        self.dim = dim
        
        # Extract parameters with optimized defaults for recall ≥95%
        M = kwargs.get('M', 32)  # Higher connectivity for better recall
        ef_construction = kwargs.get('ef_construction', 400)
        self.ef_search = kwargs.get('ef_search', 256)  # High for high recall
        
        # Create HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        
        # Set construction parameters
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Track number of vectors for batch operations
        self.ntotal = 0
        
    def add(self, xb: np.ndarray) -> None:
        """Add vectors to the index."""
        if len(xb) == 0:
            return
            
        # Add in batches to manage memory
        batch_size = 50000
        n = len(xb)
        
        for i in range(0, n, batch_size):
            end = min(i + batch_size, n)
            self.index.add(xb[i:end])
            
        self.ntotal += n
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Search for k nearest neighbors."""
        if self.ntotal == 0:
            return np.empty((len(xq), k), dtype=np.float32), np.empty((len(xq), k), dtype=np.int64)
            
        # Ensure we don't ask for more than available
        actual_k = min(k, self.ntotal)
        
        # Set search parameter for this batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Search all queries at once (batch optimization)
        distances, indices = self.index.search(xq, actual_k)
        
        # Handle case where we requested more than available
        if actual_k < k:
            # Pad with -1 for indices and inf for distances
            padded_distances = np.full((len(xq), k), np.float32('inf'))
            padded_indices = np.full((len(xq), k), -1, dtype=np.int64)
            
            padded_distances[:, :actual_k] = distances
            padded_indices[:, :actual_k] = indices
            
            return padded_distances, padded_indices
            
        return distances, indices