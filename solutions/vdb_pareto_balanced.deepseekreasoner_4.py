import numpy as np
import faiss

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall within latency constraint.
        Parameters tuned for SIFT1M (1M vectors, 128D) to achieve >0.9914 recall
        while keeping batch query time ≤ 5.775ms.
        """
        self.dim = dim
        
        # Extract parameters with optimized defaults for recall-latency tradeoff
        # HNSW parameters: M=24 (higher for better recall), ef_construction=400 (high for accuracy)
        # ef_search will be tuned based on whether we're building or searching
        self.M = kwargs.get('M', 24)  # Increased from 16 for better connectivity
        self.ef_construction = kwargs.get('ef_construction', 400)  # High for maximum recall
        self.ef_search = kwargs.get('ef_search', 128)  # Initial value, will be auto-tuned
        
        # Create HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Store vectors for fallback exact search if needed
        self.xb = None
        self.built = False
        self.n_total = 0
        
        # Set threads for efficient batch processing (8 vCPUs)
        self.threads = kwargs.get('threads', 8)
        if hasattr(faiss, 'omp_set_num_threads'):
            faiss.omp_set_num_threads(self.threads)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index incrementally.
        """
        if self.xb is None:
            self.xb = xb.astype(np.float32).copy()
        else:
            self.xb = np.vstack([self.xb, xb.astype(np.float32)])
        
        # Add to FAISS index
        self.index.add(xb.astype(np.float32))
        self.n_total += xb.shape[0]
        
        # Auto-tune ef_search based on dataset size for optimal recall-latency
        if self.n_total > 10000 and not self.built:
            self._auto_tune_parameters()

    def _auto_tune_parameters(self):
        """
        Auto-tune parameters for optimal recall-latency tradeoff.
        Uses conservative settings to ensure recall > 0.9914.
        """
        # For SIFT1M with 1M points, use higher ef_search for maximum recall
        # This ensures we meet the recall baseline of 0.9914
        if self.n_total > 500000:
            # High ef_search for maximum recall at the expense of some latency
            # Still within 5.775ms constraint due to batch optimization
            self.index.hnsw.efSearch = 200
        else:
            # Moderate ef_search for smaller datasets
            self.index.hnsw.efSearch = 128
        
        self.built = True

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors using HNSW with optimized parameters.
        Uses batch processing for efficient queries.
        """
        xq = xq.astype(np.float32)
        
        # Ensure we have enough capacity in the index
        if not self.built and self.n_total > 10000:
            self._auto_tune_parameters()
        
        # Set search parameters for maximum recall
        # Higher ef_search for better accuracy (meets recall baseline)
        current_ef = self.index.hnsw.efSearch
        if current_ef < 150 and self.n_total > 500000:
            # Bump up ef_search for large datasets to ensure high recall
            self.index.hnsw.efSearch = 200
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        # Reset ef_search if we changed it
        if current_ef < 150 and self.n_total > 500000:
            self.index.hnsw.efSearch = current_ef
        
        # Convert to required dtypes
        return distances.astype(np.float32), indices.astype(np.int64)
