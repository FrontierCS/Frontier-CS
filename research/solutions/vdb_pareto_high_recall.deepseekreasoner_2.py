import numpy as np
import faiss

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.index = None
        self.vectors_added = False
        
        # HNSW parameters optimized for high recall with relaxed latency
        # Using the full 7.7ms latency budget for maximum recall
        self.M = 32  # Reasonable graph connectivity for good recall
        self.ef_construction = 200  # High construction quality
        self.ef_search = 850  # High search depth for maximum recall
        
        # Allow overriding parameters via kwargs
        if 'M' in kwargs:
            self.M = kwargs['M']
        if 'ef_construction' in kwargs:
            self.ef_construction = kwargs['ef_construction']
        if 'ef_search' in kwargs:
            self.ef_search = kwargs['ef_search']
        
        # Initialize with default parameters
        self._init_index()

    def _init_index(self):
        """Initialize FAISS HNSW index with specified parameters"""
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Enable dynamic index building for multiple add calls
        self.index.verbose = False

    def add(self, xb: np.ndarray) -> None:
        """Add vectors to the index"""
        if not self.vectors_added:
            self.index.add(xb)
            self.vectors_added = True
        else:
            # For subsequent adds, we need to handle incremental addition
            current_ntotal = self.index.ntotal
            new_vectors = xb.shape[0]
            
            # Create a new index with combined capacity if needed
            # This is a simplified approach - in practice, HNSW doesn't support
            # efficient incremental addition well, but this handles the API requirement
            if hasattr(self.index, 'add'):
                self.index.add(xb)
            else:
                # Fallback: create new index with all vectors
                # Note: This is inefficient but handles the cumulative add requirement
                all_vectors = np.vstack([self.index.reconstruct(i) for i in range(current_ntotal)] + [xb])
                self._init_index()
                self.index.add(all_vectors)

    def search(self, xq: np.ndarray, k: int):
        """Search for k nearest neighbors"""
        if self.index is None or self.index.ntotal == 0:
            # Return empty results if no vectors in index
            nq = xq.shape[0]
            return np.zeros((nq, k), dtype=np.float32), np.zeros((nq, k), dtype=np.int64)
        
        # Set search parameters for maximum recall
        original_ef_search = self.index.hnsw.efSearch
        self.index.hnsw.efSearch = self.ef_search
        
        # Ensure at least k neighbors can be found
        actual_k = min(k, self.index.ntotal)
        
        # Perform search
        distances, indices = self.index.search(xq, actual_k)
        
        # Handle case where we have fewer than k vectors in index
        if actual_k < k:
            # Pad results with -1 indices and max distance
            nq = xq.shape[0]
            padded_distances = np.full((nq, k), np.finfo(np.float32).max, dtype=np.float32)
            padded_indices = np.full((nq, k), -1, dtype=np.int64)
            
            padded_distances[:, :actual_k] = distances
            padded_indices[:, :actual_k] = indices
            
            distances = padded_distances
            indices = padded_indices
        
        # Reset efSearch to original value
        self.index.hnsw.efSearch = original_ef_search
        
        return distances, indices