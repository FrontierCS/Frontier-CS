import numpy as np
import faiss

class FastIVFIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.index = None
        
        # Optimized parameters for latency with ~80% recall
        nlist = 4096  # Number of clusters
        nprobe = 3    # Search in 3 closest clusters
        
        # Create quantizer
        quantizer = faiss.IndexFlatL2(dim)
        
        # Create IVF index with minimal overhead
        self.index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)
        
        # Set nprobe for search
        self.index.nprobe = nprobe
        
        # Enable parallel computation
        faiss.omp_set_num_threads(8)
        
        # Store for training if needed
        self.is_trained = False
        
    def add(self, xb: np.ndarray) -> None:
        if not self.is_trained:
            # Train on first batch (use all data)
            self.index.train(xb)
            self.is_trained = True
        
        # Add vectors to index
        self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int) -> tuple:
        # Ensure k doesn't exceed number of vectors
        k = min(k, self.index.ntotal)
        
        # Search with precomputed distances flag for speed
        distances = np.empty((xq.shape[0], k), dtype=np.float32)
        indices = np.empty((xq.shape[0], k), dtype=np.int64)
        
        # Perform search
        self.index.search(xq, k, distances, indices)
        
        return distances, indices