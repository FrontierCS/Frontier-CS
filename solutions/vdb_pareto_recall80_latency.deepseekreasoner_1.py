import numpy as np
import faiss

class Recall80LatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # IVF parameters optimized for latency while maintaining ~80% recall
        self.nlist = 1024  # Number of Voronoi cells
        self.nprobe = 1    # Number of cells to visit (kept minimal for speed)
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe
        self.is_trained = False
        
        # Override with any provided kwargs
        if 'nlist' in kwargs:
            self.nlist = kwargs['nlist']
        if 'nprobe' in kwargs:
            self.nprobe = kwargs['nprobe']
            
        # Reinitialize with custom parameters if provided
        if 'nlist' in kwargs or 'nprobe' in kwargs:
            self.quantizer = faiss.IndexFlatL2(dim)
            self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
            self.index.nprobe = self.nprobe
            
        # Training sample size (subset for faster training)
        self.train_samples = min(100000, 100 * self.nlist)

    def add(self, xb: np.ndarray) -> None:
        # Train on a subset if not already trained
        if not self.is_trained:
            if len(xb) > self.train_samples:
                # Sample training data
                np.random.seed(123)
                sample_indices = np.random.choice(len(xb), self.train_samples, replace=False)
                train_data = xb[sample_indices]
            else:
                train_data = xb
                
            self.index.train(train_data)
            self.is_trained = True
        
        # Add the vectors
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int):
        # Ensure k doesn't exceed number of vectors in index
        actual_k = min(k, self.index.ntotal) if self.index.ntotal > 0 else k
        
        # Perform the search
        distances, indices = self.index.search(xq, actual_k)
        
        # If we asked for more neighbors than available, pad with -1 and large distances
        if actual_k < k:
            padded_distances = np.full((len(xq), k), np.finfo(np.float32).max, dtype=np.float32)
            padded_indices = np.full((len(xq), k), -1, dtype=np.int64)
            padded_distances[:, :actual_k] = distances
            padded_indices[:, :actual_k] = indices
            distances, indices = padded_distances, padded_indices
        
        return distances.astype(np.float32), indices.astype(np.int64)
