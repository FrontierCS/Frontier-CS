import numpy as np
import faiss

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index for SIFT1M with optimized parameters for recall.
        Default parameters tuned to achieve high recall while meeting latency constraint.
        """
        self.dim = dim
        
        # Extract parameters or use optimized defaults for SIFT1M
        M = kwargs.get('M', 24)  # Increased from 16 for better recall
        ef_construction = kwargs.get('ef_construction', 400)  # High for better graph
        ef_search = kwargs.get('ef_search', 128)  # High for better recall
        
        # Create HNSW index with flat storage (exact distance calculation)
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        
        # Optimize search parameters
        self.index.hnsw.search_bounded_queue = False
        
        # Set number of threads for batch queries (8 vCPUs)
        self.threads = kwargs.get('threads', 8)
        faiss.omp_set_num_threads(self.threads)
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int):
        """
        Search for k nearest neighbors using HNSW with optimized settings.
        """
        # Set efSearch for this search operation
        self.index.hnsw.efSearch = 128
        
        # Perform the search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)