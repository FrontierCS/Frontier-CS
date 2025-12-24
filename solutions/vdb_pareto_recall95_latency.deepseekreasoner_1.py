import numpy as np
import faiss

class HNSWIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        
        # HNSW parameters optimized for 95%+ recall with low latency
        M = kwargs.get('M', 24)  # Increased from 16 for better recall
        ef_construction = kwargs.get('ef_construction', 400)  # High construction quality
        self.ef_search = kwargs.get('ef_search', 64)  # Balanced recall vs speed
        
        # Create HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Store for debugging/inspection
        self.vectors_added = 0
        
    def add(self, xb: np.ndarray) -> None:
        # Ensure input is contiguous and correct dtype
        xb = np.ascontiguousarray(xb.astype(np.float32))
        self.index.add(xb)
        self.vectors_added += xb.shape[0]
        
    def search(self, xq: np.ndarray, k: int) -> tuple:
        # Ensure input is contiguous and correct dtype
        xq = np.ascontiguousarray(xq.astype(np.float32))
        
        # Pre-allocate output arrays
        nq = xq.shape[0]
        distances = np.empty((nq, k), dtype=np.float32)
        indices = np.empty((nq, k), dtype=np.int64)
        
        # Perform search
        self.index.search(xq, k, distances, indices)
        
        return distances, indices
