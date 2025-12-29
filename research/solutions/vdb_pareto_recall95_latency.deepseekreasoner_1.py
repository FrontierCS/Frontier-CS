import numpy as np
import faiss

class Recall95LatencyOptimizedIndex:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW index optimized for high recall (≥95%) with low latency.
        Uses parameters tuned for SIFT1M dataset (128 dimensions).
        """
        self.dim = dim
        
        # HNSW parameters optimized for recall@1 ≥ 95% and low latency
        # M: number of connections per node (higher = better recall, slower)
        # efConstruction: construction-time search scope (higher = better graph)
        # efSearch: query-time search scope (higher = better recall, slower)
        
        # Conservative parameters to ensure >95% recall while being fast
        M = kwargs.get('M', 32)  # Moderate connectivity for speed
        ef_construction = kwargs.get('ef_construction', 200)  # High for good graph
        self.ef_search = kwargs.get('ef_search', 128)  # High enough for >95% recall
        
        # Create HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # For batch search optimization
        self.index.verbose = False
        
    def add(self, xb: np.ndarray) -> None:
        """Add vectors to the index."""
        if not self.index.is_trained:
            self.index.train(xb[:min(10000, len(xb))])
        self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors.
        Optimized for batch queries (10K queries at once).
        """
        # Set efSearch for this batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)