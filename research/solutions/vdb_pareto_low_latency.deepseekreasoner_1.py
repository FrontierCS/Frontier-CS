import numpy as np
import faiss

class FastHNSWIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # Optimized for low latency: small M, low efConstruction
        # Targeting recall around 0.85-0.90 while staying under 2.31ms
        self.M = kwargs.get('M', 12)  # Reduced from typical 16 for faster search
        self.ef_construction = kwargs.get('ef_construction', 64)  # Low for fast build
        self.ef_search = kwargs.get('ef_search', 32)  # Aggressively low for speed
        self.index = None
        
    def add(self, xb: np.ndarray) -> None:
        if self.index is None:
            # Use L2 distance (Euclidean)
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.add(xb)
        else:
            self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int):
        if self.index is None:
            raise RuntimeError("Index not initialized. Call add() first.")
        
        # Set search parameter for this batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        # Return as float32 and int64 to match API
        return distances.astype(np.float32), indices.astype(np.int64)