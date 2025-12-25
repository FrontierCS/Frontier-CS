import numpy as np
import faiss

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize an IVF index optimized for low latency.
        Uses aggressive parameters to meet 2.31ms constraint.
        """
        self.dim = dim
        
        # IVF parameters optimized for SIFT1M with strict latency constraint
        nlist = 1024  # Number of Voronoi cells (clusters)
        nprobe = 4    # Number of cells to search (very aggressive for speed)
        
        # Quantizer for coarse clustering
        quantizer = faiss.IndexFlatL2(dim)
        
        # Create IVF index with inner product (will be converted to L2)
        self.index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)
        
        # Set aggressive search parameters for low latency
        self.index.nprobe = nprobe
        
        # Training parameters
        self.index.cp.min_points_per_centroid = 5  # Fewer points per centroid
        self.index.cp.max_points_per_centroid = 1000000  # Allow many points
        
        # Parallelization settings for batch queries
        faiss.omp_set_num_threads(8)  # Use all available CPU cores
        
        # Track if trained
        self.is_trained = False
        self.vectors_added = 0
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index with incremental training if needed.
        """
        n_vectors = xb.shape[0]
        
        # Train on first batch if not trained
        if not self.is_trained:
            # Train on a subset for faster training (20% of data)
            train_size = min(200000, n_vectors)
            train_vectors = xb[:train_size].copy()
            self.index.train(train_vectors)
            self.is_trained = True
        
        # Add vectors in batches to manage memory
        batch_size = 50000
        for i in range(0, n_vectors, batch_size):
            end_idx = min(i + batch_size, n_vectors)
            self.index.add(xb[i:end_idx])
        
        self.vectors_added += n_vectors
        
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors using batch processing.
        Optimized for batch queries with aggressive IVF settings.
        """
        # Ensure k is at least 1 and doesn't exceed available vectors
        k = max(1, min(k, self.vectors_added))
        
        # Prepare output arrays
        nq = xq.shape[0]
        distances = np.empty((nq, k), dtype=np.float32)
        indices = np.empty((nq, k), dtype=np.int64)
        
        # Search in batches to optimize cache usage
        batch_size = 1000  # Optimal for CPU cache
        for i in range(0, nq, batch_size):
            end_idx = min(i + batch_size, nq)
            batch_xq = xq[i:end_idx]
            
            # Perform search with current nprobe setting
            batch_dist, batch_idx = self.index.search(batch_xq, k)
            
            # Store results
            distances[i:end_idx] = batch_dist
            indices[i:end_idx] = batch_idx
        
        return distances, indices
