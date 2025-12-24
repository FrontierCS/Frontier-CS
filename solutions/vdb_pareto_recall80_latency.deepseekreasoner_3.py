import numpy as np
import faiss

class Recall80LatencyTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize index optimized for latency with recall constraint.
        Uses IVF index with minimal probes for extreme speed.
        """
        self.dim = dim
        
        # Extract parameters or use defaults optimized for latency
        self.nlist = kwargs.get('nlist', 1024)  # Number of IVF cells
        self.nprobe = kwargs.get('nprobe', 1)   # Minimal probes for speed
        
        # Create IVF index with flat (exact) storage
        quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        # Training will be done on first batch of data
        self.is_trained = False
        
        # For tracking total vectors added
        self.total_vectors = 0
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. Train if not already trained.
        """
        if not self.is_trained:
            # Train on the first batch (or subset for faster training)
            n_train = min(100000, len(xb))
            self.index.train(xb[:n_train])
            self.is_trained = True
        
        # Add vectors to index
        self.index.add(xb)
        self.total_vectors += len(xb)
        
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors with minimal probes for speed.
        """
        # Set nprobe parameter (controls speed/accuracy tradeoff)
        self.index.nprobe = self.nprobe
        
        # Pre-allocate for maximum performance
        nq = xq.shape[0]
        distances = np.empty((nq, k), dtype=np.float32)
        indices = np.empty((nq, k), dtype=np.int64)
        
        # Perform search
        distances[:], indices[:] = self.index.search(xq, k)
        
        return distances, indices
