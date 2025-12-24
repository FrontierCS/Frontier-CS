import numpy as np
import faiss

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters
        """
        self.dim = dim
        
        # Use IVF index with very low nprobe for aggressive approximation
        # IVF indexes are cache-friendly for batch queries
        self.nlist = kwargs.get('nlist', 512)  # Number of clusters
        self.nprobe = kwargs.get('nprobe', 2)  # Number of clusters to visit (VERY low for speed)
        self.use_gpu = kwargs.get('use_gpu', False)
        
        # Create quantizer (coarse quantizer for IVF)
        quantizer = faiss.IndexFlatL2(dim)
        
        # Create IVF index with Flat storage (exact distances within clusters)
        # This is faster than PQ for batch queries due to SIMD optimization
        self.index = faiss.IndexIVFFlat(quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        # Enable parallel processing for batch queries
        self.index.parallel_mode = 3  # Enable parallel search (0=no parallelism, 3=most aggressive)
        
        # Track if index is trained
        self.is_trained = False
        self.vectors_added = 0

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        
        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # Train on the first batch of vectors (or a sample if too large)
            if xb.shape[0] >= self.nlist * 39:  # FAISS recommends ~39 vectors per centroid
                self.index.train(xb)
                self.is_trained = True
            else:
                # For small batches, we need to accumulate or use random training
                # In SIFT1M, we get 1M vectors at once, so this won't be called
                pass
        
        if self.is_trained:
            self.index.add(xb)
            self.vectors_added += xb.shape[0]
        else:
            # For the SIFT1M case, we'll have enough vectors to train immediately
            # But just in case of incremental addition, handle it
            self.index.train(xb[:min(xb.shape[0], 20000)])
            self.is_trained = True
            self.index.add(xb)
            self.vectors_added += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors of query vectors.
        
        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return
            
        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        # Set nprobe for this search (very low for speed)
        self.index.nprobe = self.nprobe
        
        # Perform the search
        distances, indices = self.index.search(xq, k)
        
        # FAISS returns squared L2 distances by default, which is fine
        # as the ordering is the same and we save sqrt computation
        return distances.astype(np.float32), indices.astype(np.int64)
