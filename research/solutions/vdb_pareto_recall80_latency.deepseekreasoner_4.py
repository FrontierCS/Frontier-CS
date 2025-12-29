import numpy as np
import faiss

class Recall80LatencyTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Optimized for latency while maintaining recall >= 80%.
        Uses IVF with very aggressive parameters (nprobe=1) for minimal latency.
        """
        self.dim = dim
        
        # Use IVF with very few clusters and nprobe=1 for minimal latency
        nlist = kwargs.get('nlist', 256)  # Few clusters for speed
        self.nprobe = kwargs.get('nprobe', 1)  # Check only 1 cluster per query
        
        # Create quantizer and IVF index
        quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)
        
        # Don't train immediately - wait for add()
        self.is_trained = False
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index, training if necessary.
        """
        if not self.is_trained:
            # Train on the data (or a subset for speed)
            train_size = min(100000, len(xb))
            train_data = xb[:train_size]
            self.index.train(train_data)
            self.is_trained = True
        
        # Add the vectors
        self.index.add(xb)
        
        # Set nprobe parameter for future searches
        self.index.nprobe = self.nprobe
    
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors with minimal latency.
        Uses batch processing for efficiency.
        """
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)