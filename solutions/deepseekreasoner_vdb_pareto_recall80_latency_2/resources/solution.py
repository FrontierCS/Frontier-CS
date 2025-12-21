import numpy as np
import faiss

class Recall80LatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Optimized index for SIFT1M with recall >= 0.80 and latency < 0.6ms
        Uses IVF with very small nprobe for extreme speed
        """
        self.dim = dim
        self.nlist = kwargs.get('nlist', 2048)  # Coarse quantizer cells
        self.nprobe = kwargs.get('nprobe', 1)   # Extremely aggressive for latency
        self.quantizer = None
        self.index = None
        
    def add(self, xb: np.ndarray) -> None:
        """
        Build IVF index with training on subset of data
        """
        n_samples = min(100000, len(xb))
        train_data = xb[:n_samples].copy()
        
        # Create and train quantizer
        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist)
        self.index.train(train_data)
        
        # Add all vectors
        self.index.add(xb)
        self.index.nprobe = self.nprobe
    
    def search(self, xq: np.ndarray, k: int):
        """
        Search with minimal nprobe for extreme latency optimization
        """
        # Ensure nprobe is set to minimal value
        self.index.nprobe = self.nprobe
        
        # Batch search - faiss handles vectorization efficiently
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
