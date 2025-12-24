import numpy as np
import faiss
import time

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index for high recall with relaxed latency constraint.
        
        Parameters tuned for SIFT1M with 7.7ms latency budget:
        - M: Number of connections per node (higher = better recall, slower)
        - efConstruction: Construction time/quality tradeoff
        - efSearch: Search quality parameter (higher = better recall, slower)
        """
        self.dim = dim
        
        # HNSW parameters optimized for high recall within 7.7ms
        # Using higher M and efSearch than balanced tier for better recall
        self.M = kwargs.get('M', 64)  # High connectivity for better recall
        self.efConstruction = kwargs.get('ef_construction', 400)
        self.efSearch = kwargs.get('ef_search', 800)  # High for maximum recall
        
        # Initialize HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.efConstruction
        
        # Store for potential reindexing if needed
        self.vectors = None
        self.built = False
        
        # Set threads for batch query optimization
        self.threads = 8  # Using all available vCPUs

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. Can be called multiple times.
        """
        if self.vectors is None:
            self.vectors = xb.copy()
        else:
            self.vectors = np.vstack([self.vectors, xb])
        
        # Rebuild index with all vectors
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the HNSW index with current vectors"""
        if self.vectors is not None:
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.hnsw.efConstruction = self.efConstruction
            self.index.add(self.vectors)
            self.built = True

    def search(self, xq: np.ndarray, k: int):
        """
        Search for k nearest neighbors with high recall optimization.
        
        Uses high efSearch for maximum recall within latency budget.
        Optimizes batch query performance with threading.
        """
        if not self.built:
            raise RuntimeError("Index not built. Call add() first.")
        
        # Set search parameters for high recall
        self.index.hnsw.efSearch = self.efSearch
        
        # Set number of threads for batch query optimization
        faiss.omp_set_num_threads(self.threads)
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
