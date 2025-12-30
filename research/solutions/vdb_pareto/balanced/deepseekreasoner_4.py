import numpy as np
import faiss
from typing import Tuple
import os

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index with optimized parameters for recall.
        We use HNSW as it provides excellent recall-speed tradeoff.
        """
        self.dim = dim
        
        # HNSW parameters tuned for high recall while meeting latency constraint
        # M: number of neighbors per node (higher = better recall, slower)
        # efConstruction: construction time/quality tradeoff
        # efSearch: search quality/speed tradeoff
        
        # Optimized parameters for SIFT1M (128D) to maximize recall while staying under 5.775ms
        self.M = kwargs.get('M', 32)  # Increased for better recall
        self.ef_construction = kwargs.get('ef_construction', 400)  # High for maximum recall
        self.ef_search = kwargs.get('ef_search', 128)  # Increased for maximum recall
        
        # Initialize HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Set number of threads for parallel processing (8 vCPUs available)
        self.omp_threads = min(8, os.cpu_count() or 1)
        faiss.omp_set_num_threads(self.omp_threads)
        
        # Store vectors for potential re-indexing if needed
        self.stored_vectors = None
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index incrementally.
        For HNSW, we can add vectors directly.
        """
        if self.stored_vectors is None:
            self.stored_vectors = xb.copy()
        else:
            self.stored_vectors = np.vstack([self.stored_vectors, xb])
        
        # Add to FAISS index
        self.index.add(xb)
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        Uses batch processing for efficient querying.
        """
        # Ensure efSearch is set for this search operation
        # We might adjust ef_search based on batch size for optimal performance
        current_ef_search = self.ef_search
        
        # For large batches, we can potentially use slightly lower ef_search
        # due to better cache utilization, but we want maximum recall
        if len(xq) > 1000:
            # Keep high ef_search for maximum recall
            current_ef_search = self.ef_search
        else:
            # For smaller batches, we can use the full ef_search
            current_ef_search = self.ef_search
        
        self.index.hnsw.efSearch = current_ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        # FAISS returns squared L2 distances by default for IndexHNSWFlat
        # We'll return them as is (squared distances are fine for ranking)
        # If L2 distances are needed, we could take sqrt, but that's slower
        # and not necessary for recall calculation
        
        return distances.astype(np.float32), indices.astype(np.int64)