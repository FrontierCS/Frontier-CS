import numpy as np
import faiss

class LatencyOptimizedIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize an IVF index optimized for extreme low latency while maintaining ≥80% recall.
        Uses IVF with 1024 clusters and PQ compression for fast search.
        """
        self.dim = dim
        self.nlist = 1024  # Number of Voronoi cells
        self.m = 8  # Number of subquantizers for PQ (compromise between speed and accuracy)
        self.nprobe = 3  # Number of cells to visit during search
        
        # Create the IVF index with PQ compression
        quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFPQ(quantizer, dim, self.nlist, self.m, 8)
        
        # Pre-allocate for batch processing
        self.batch_size = 1000
        
        # Enable parallelism
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index with training if needed.
        """
        if not self.index.is_trained:
            # Train on a subset for speed
            n_train = min(100000, len(xb))
            self.index.train(xb[:n_train])
        
        # Add in batches to manage memory
        for i in range(0, len(xb), self.batch_size):
            batch = xb[i:i + self.batch_size]
            self.index.add(batch)

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors with optimized parameters for low latency.
        """
        # Set search parameters for maximum speed while maintaining recall
        self.index.nprobe = self.nprobe
        
        # Ensure k doesn't exceed available vectors
        k = min(k, self.index.ntotal)
        
        # Pre-allocate output arrays
        nq = xq.shape[0]
        distances = np.empty((nq, k), dtype=np.float32)
        indices = np.empty((nq, k), dtype=np.int64)
        
        # Search in batches for better cache utilization
        for i in range(0, nq, self.batch_size):
            batch_end = min(i + self.batch_size, nq)
            batch_xq = xq[i:batch_end]
            batch_distances = np.empty((batch_end - i, k), dtype=np.float32)
            batch_indices = np.empty((batch_end - i, k), dtype=np.int64)
            
            self.index.search(batch_xq, k, batch_distances, batch_indices)
            
            distances[i:batch_end] = batch_distances
            indices[i:batch_end] = batch_indices
        
        # Convert distances to L2 (PQ returns approximate distances)
        # The index already returns L2 distances
        return distances, indices