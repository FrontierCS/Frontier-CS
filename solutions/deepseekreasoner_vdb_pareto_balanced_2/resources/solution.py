import numpy as np
import faiss

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index with optimized parameters for SIFT1M.
        Parameters tuned for high recall while meeting latency constraint.
        """
        self.dim = dim
        
        # HNSW parameters optimized for SIFT1M
        # M=16: Good balance between recall and memory
        # efConstruction=200: High construction quality for better recall
        # efSearch=64: Good recall with reasonable speed (can be adjusted)
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 64)
        
        # Create HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Enable distance computation
        self.index.metric_type = faiss.METRIC_L2
        
        # Store vectors for potential re-indexing
        self.xb_list = []
        self.is_trained = False

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. For HNSW, we can add incrementally.
        """
        # Store vectors in case we need to rebuild
        self.xb_list.append(xb.copy())
        
        # Add to index
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors using HNSW.
        Returns squared L2 distances for efficiency.
        """
        # Ensure k doesn't exceed number of vectors in index
        if self.index.ntotal == 0:
            return np.empty((xq.shape[0], k), dtype=np.float32), np.empty((xq.shape[0], k), dtype=np.int64)
        
        # Set efSearch parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search - returns squared L2 distances
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
