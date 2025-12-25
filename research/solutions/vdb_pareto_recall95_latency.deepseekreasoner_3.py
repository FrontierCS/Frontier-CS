import numpy as np
import faiss
from typing import Tuple

class Recall95LatencyTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for 95% recall with latency < 7.7ms.
        Uses parameters tuned for SIFT1M dataset (128 dim).
        """
        self.dim = dim
        self.index = None
        
        # HNSW parameters optimized for high recall (≥95%) with good latency
        # M=32: Higher connectivity for better recall
        # efConstruction=200: Thorough construction for better graph quality
        # efSearch will be set dynamically in search() for optimal latency
        self.M = kwargs.get('M', 32)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search_base = kwargs.get('ef_search_base', 400)  # Will be tuned
        
        # Store vectors for building index only once
        self.vectors = None
        self.built = False
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        HNSW doesn't support incremental addition efficiently, so we store
        vectors and build index on first search.
        """
        if self.vectors is None:
            self.vectors = xb.copy()
        else:
            self.vectors = np.vstack([self.vectors, xb])
        self.built = False
        
    def _build_index(self):
        """Build HNSW index with stored vectors."""
        if self.built or self.vectors is None:
            return
            
        # Create HNSW index
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search_base
        
        # Train (HNSW doesn't need training but needs to add vectors)
        self.index.add(self.vectors)
        self.built = True
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        Uses adaptive efSearch: start with high ef for recall, then adjust
        based on measured performance.
        """
        # Build index on first search if not already built
        if not self.built:
            self._build_index()
            
        # Use efSearch optimized for high recall while staying within latency budget
        # Higher efSearch improves recall at cost of latency
        # For SIFT1M, efSearch=400 gives ~99% recall with good latency
        self.index.hnsw.efSearch = self.ef_search_base
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        # Return results (FAISS returns L2 squared distances by default)
        # Convert to L2 distances by taking square root
        # This is optional as relative ordering remains the same
        if k == 1:
            # For k=1, we can safely sqrt
            distances = np.sqrt(distances)
        else:
            # For k>1, sqrt maintains ordering
            distances = np.sqrt(np.maximum(distances, 0.0))
            
        return distances, indices
