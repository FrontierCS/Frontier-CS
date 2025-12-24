import numpy as np
import faiss

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall within relaxed latency.
        """
        self.dim = dim
        # HNSW parameters tuned for recall-first tier (2x latency budget)
        self.M = kwargs.get('M', 64)  # high connectivity for recall
        self.ef_construction = kwargs.get('ef_construction', 500)  # high construction quality
        self.ef_search = kwargs.get('ef_search', 800)  # high search effort for max recall
        self.index = None
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.
        """
        if self.index is None:
            # Initialize index with L2 distance
            self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search
        
        # Ensure contiguous memory layout for optimal performance
        xb_contiguous = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb_contiguous)
    
    def search(self, xq: np.ndarray, k: int):
        """
        Search for k nearest neighbors using optimized batch queries.
        """
        if self.index is None or self.index.ntotal == 0:
            raise RuntimeError("Index not initialized or empty")
        
        # Ensure contiguous memory layout and float32
        xq_contiguous = np.ascontiguousarray(xq, dtype=np.float32)
        
        # Pre-allocate output arrays for better performance
        distances = np.empty((len(xq_contiguous), k), dtype=np.float32)
        indices = np.empty((len(xq_contiguous), k), dtype=np.int64)
        
        # Perform search with current efSearch setting
        self.index.search(xq_contiguous, k, distances, indices)
        
        return distances, indices
