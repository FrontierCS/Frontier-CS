import numpy as np
import faiss
import heapq
import math

class Recall95Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index with parameters optimized for SIFT1M.
        Uses HNSW with parameters tuned for high recall (>95%) within 7.7ms.
        """
        self.dim = dim
        
        # HNSW parameters tuned for SIFT1M to achieve >95% recall
        # M controls the number of neighbors in the graph (higher = better recall, slower)
        # efConstruction controls graph quality during build
        # efSearch controls search depth (higher = better recall, slower)
        self.M = kwargs.get('M', 32)  # Balanced between speed and quality
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 128)  # Optimized for 95%+ recall
        self.nprobe = kwargs.get('nprobe', 16)  # For IVF component
        
        # Use HNSW for high recall at reasonable speed
        # HNSW is generally good for high recall requirements
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # For faster search in batch mode
        self.quantizer = None
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        if not self.index.is_trained:
            self.index.train(xb)
        self.index.add(xb)
        
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors of query vectors.
        Uses batch processing optimized for SIFT1M.
        """
        # Set efSearch for this search
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform the search
        distances, indices = self.index.search(xq, k)
        
        return distances, indices