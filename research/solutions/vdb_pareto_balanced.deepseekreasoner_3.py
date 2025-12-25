import numpy as np
import faiss

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index with optimized parameters for recall-latency tradeoff.
        """
        self.dim = dim
        # HNSW parameters tuned for recall with latency constraint
        self.M = kwargs.get('M', 32)  # Higher M for better recall
        self.ef_construction = kwargs.get('ef_construction', 400)  # High construction for quality
        self.ef_search = kwargs.get('ef_search', 128)  # High ef_search for recall
        
        # Create HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Store vectors for incremental addition
        self.vectors = []
        self.built = False

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. Supports incremental addition.
        """
        if len(self.vectors) == 0:
            self.vectors = xb.copy()
        else:
            self.vectors = np.vstack([self.vectors, xb])
        self.built = False

    def _build_index(self):
        """Build or rebuild the index with accumulated vectors."""
        if not self.built:
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search
            self.index.add(self.vectors)
            self.built = True

    def search(self, xq: np.ndarray, k: int):
        """
        Search for k nearest neighbors. Ensures exactly k results.
        """
        if not self.built:
            self._build_index()
        
        # Set efSearch for this query batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
