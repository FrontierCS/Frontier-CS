import numpy as np
import faiss
import time
from typing import Tuple

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall within relaxed latency constraint.
        Uses higher efSearch and M parameters to maximize recall while staying under 7.7ms.
        """
        self.dim = dim
        
        # HNSW parameters optimized for recall (using 2x latency budget)
        # Higher M for better recall at construction time
        # Higher efSearch for exhaustive search during query
        M = kwargs.get('M', 32)  # Increased from typical 16-24 for better connectivity
        efConstruction = kwargs.get('ef_construction', 200)  # High for better graph quality
        self.efSearch = kwargs.get('ef_search', 500)  # Will be tuned per query batch
        
        # Create HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = efConstruction
        self.index.verbose = False
        
        # Store vectors for potential reindexing if needed
        self.vectors = None
        self.is_trained = True  # HNSW doesn't require training
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        if self.vectors is None:
            self.vectors = xb.astype(np.float32)
        else:
            self.vectors = np.vstack([self.vectors, xb.astype(np.float32)])
        
        # Add to HNSW index
        self.index.add(xb.astype(np.float32))
        
        # Optimize efSearch based on dataset size
        # Higher efSearch for larger datasets to maintain recall
        n_vectors = self.index.ntotal
        if n_vectors > 500000:
            self.efSearch = min(800, self.efSearch * 1.2)  # Cap at 800 for latency
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors with adaptive efSearch for batch queries.
        """
        # Set efSearch for this batch - using high value for maximum recall
        # The relaxed latency constraint (7.7ms) allows higher efSearch
        self.index.hnsw.efSearch = self.efSearch
        
        # Convert to float32 for FAISS
        xq = xq.astype(np.float32)
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
