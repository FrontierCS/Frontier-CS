import numpy as np
import faiss

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.index = None
        # Optimized for recall: HNSW with high connectivity and search parameters
        self.M = kwargs.get('M', 64)  # High connectivity for better recall
        self.ef_construction = kwargs.get('ef_construction', 500)  # High for quality build
        self.ef_search = kwargs.get('ef_search', 800)  # High for recall within 7.7ms budget
        
    def add(self, xb: np.ndarray) -> None:
        if self.index is None:
            # Create HNSW index
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.verbose = False
        self.index.add(xb)
        
    def search(self, xq: np.ndarray, k: int) -> tuple:
        # Set efSearch for this search operation
        if hasattr(self.index.hnsw, 'efSearch'):
            self.index.hnsw.efSearch = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)