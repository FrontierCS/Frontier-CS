import numpy as np
import faiss

class HighRecallHNSW:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall within relaxed latency constraints.
        
        Parameters tuned for SIFT1M with 7.7ms latency budget:
        - M: 64 (high connectivity for better recall)
        - ef_construction: 200 (build high-quality graph)
        - ef_search: 800 (thorough search for high recall)
        """
        self.dim = dim
        
        # Extract parameters with defaults optimized for high recall
        self.M = kwargs.get('M', 64)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 800)
        
        # Initialize HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.
        """
        self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors using HNSW with high ef_search.
        
        Note: Uses batch processing for efficiency with 10K queries.
        """
        # Set ef_search for this query batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Search with HNSW
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
