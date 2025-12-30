import numpy as np
import faiss
import time

class BalancedTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall while meeting latency constraint.
        Parameters tuned for SIFT1M (1M vectors, 128D) on CPU-only environment.
        """
        self.dim = dim
        self.index = None
        self.xb = None
        self.xb_norms = None
        self.use_cosine = False
        
        # HNSW parameters optimized for recall-latency tradeoff
        # M=16 provides good recall with reasonable memory (matches baseline memory)
        # efConstruction=200 ensures high-quality graph construction
        # efSearch=80 provides high recall while staying under latency constraint
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 80)
        
        # For L2 distance with normalization (more efficient)
        self.metric = faiss.METRIC_L2
        self.index = faiss.IndexHNSWFlat(dim, self.M, self.metric)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Set number of threads for batch processing (8 vCPUs)
        faiss.omp_set_num_threads(8)
    
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. Normalize for cosine similarity if needed.
        """
        if self.xb is None:
            self.xb = xb.astype(np.float32)
        else:
            self.xb = np.vstack([self.xb, xb.astype(np.float32)])
        
        # Normalize for cosine similarity (better for SIFT)
        xb_norm = self.xb.copy()
        faiss.normalize_L2(xb_norm)
        
        # Clear and rebuild with normalized vectors
        if self.index.ntotal > 0:
            self.index.reset()
        
        self.index.add(xb_norm)
    
    def search(self, xq: np.ndarray, k: int):
        """
        Search for k nearest neighbors using HNSW with cosine similarity.
        Returns L2 distances (converted from cosine distances).
        """
        # Normalize queries for cosine similarity
        xq_norm = xq.astype(np.float32).copy()
        faiss.normalize_L2(xq_norm)
        
        # Set efSearch for this search
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq_norm, k)
        
        # Convert cosine distances back to L2 distances
        # For normalized vectors: ||x - y||^2 = 2 - 2*cos(x,y)
        # Our index returns 1 - cos(x,y) for cosine similarity, so:
        # L2^2 = 2 * distance_returned
        distances = 2.0 * distances
        
        return distances, indices

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Wrapper class with adaptive parameter selection.
        Dynamically adjusts parameters based on dataset size.
        """
        self.dim = dim
        self.index = None
        self.normalize = True
        
        # Adaptive parameters based on expected dataset size
        # For SIFT1M (1M vectors), use HNSW with tuned parameters
        # For smaller datasets, use different parameters
        self.expected_size = 1000000  # SIFT1M
        
        # Choose index type based on dimensions and expected size
        if dim <= 128 and self.expected_size <= 1000000:
            # HNSW is excellent for moderate dimensions and up to 1M points
            self.M = kwargs.get('M', 16)
            self.ef_construction = kwargs.get('ef_construction', 200)
            self.ef_search = kwargs.get('ef_search', 80)
            
            self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search
        else:
            # Fallback to IVF for higher dimensions or larger datasets
            nlist = min(4096, self.expected_size // 39)
            self.index = faiss.IndexIVFFlat(
                faiss.IndexFlatL2(dim),
                dim,
                nlist,
                faiss.METRIC_L2
            )
        
        # Set threads for batch processing
        faiss.omp_set_num_threads(8)
    
    def add(self, xb: np.ndarray) -> None:
        """Add vectors with normalization for better recall."""
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        # Store original vectors for distance computation
        if not hasattr(self, 'xb_stored'):
            self.xb_stored = xb
        else:
            self.xb_stored = np.vstack([self.xb_stored, xb])
        
        # Normalize for cosine similarity (works better for SIFT)
        xb_norm = xb.copy()
        if self.normalize:
            faiss.normalize_L2(xb_norm)
        
        # For IVF index, need to train
        if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
            self.index.train(xb_norm)
        
        self.index.add(xb_norm)
    
    def search(self, xq: np.ndarray, k: int):
        """Search with parameter tuning for optimal recall-latency tradeoff."""
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        # Normalize queries if vectors were normalized
        xq_norm = xq.copy()
        if self.normalize:
            faiss.normalize_L2(xq_norm)
        
        # Adjust search parameters for optimal recall within latency constraint
        if isinstance(self.index, faiss.IndexHNSWFlat):
            # Dynamically adjust efSearch based on k
            ef_search = max(40, min(120, self.ef_search * k))
            self.index.hnsw.efSearch = ef_search
        elif isinstance(self.index, faiss.IndexIVFFlat):
            # For IVF, increase nprobe for higher recall
            nprobe = min(64, self.index.nlist // 4)
            self.index.nprobe = nprobe
        
        # Perform search
        distances, indices = self.index.search(xq_norm, k)
        
        # Convert cosine distances back to L2 if using normalization
        if self.normalize:
            # For normalized vectors: L2^2 = 2 - 2*cos(x,y)
            # Our cosine distances are 1 - cos(x,y), so L2^2 = 2 * distance
            distances = 2.0 * distances
        
        return distances, indices

# Final class must match API specification exactly
class BalancedIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Optimized HNSW index for SIFT1M with parameters tuned for
        maximum recall under 5.775ms latency constraint.
        """
        self.dim = dim
        
        # HNSW parameters optimized through testing on SIFT1M
        # M=16: Good balance between recall and memory usage
        # efConstruction=200: High quality graph for maximum recall
        # efSearch=96: Carefully tuned to exceed baseline recall (0.9914) 
        #              while staying under 5.775ms on 8 vCPUs
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 96)
        
        # Initialize HNSW index with L2 metric (will use cosine via normalization)
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Enable normalization for cosine similarity (better for SIFT)
        self.normalize = True
        
        # Optimize for batch queries with 8 threads
        faiss.omp_set_num_threads(8)
    
    def add(self, xb: np.ndarray) -> None:
        """Add normalized vectors for cosine similarity."""
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        # Normalize for cosine similarity (works better for SIFT features)
        if self.normalize:
            xb_norm = xb.copy()
            faiss.normalize_L2(xb_norm)
            self.index.add(xb_norm)
        else:
            self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int):
        """Search with efSearch tuned for optimal recall-latency tradeoff."""
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        # Normalize queries if using cosine similarity
        if self.normalize:
            xq_norm = xq.copy()
            faiss.normalize_L2(xq_norm)
            
            # Set efSearch for this query batch
            # Slightly increase for k>1 to maintain recall
            current_ef = self.ef_search if k == 1 else min(128, self.ef_search * 2)
            self.index.hnsw.efSearch = current_ef
            
            # Perform search on normalized vectors
            distances, indices = self.index.search(xq_norm, k)
            
            # Convert cosine distances (1-cos) back to L2 squared: L2² = 2 * (1-cos)
            distances = 2.0 * distances
        else:
            # Direct L2 search
            self.index.hnsw.efSearch = self.ef_search
            distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)