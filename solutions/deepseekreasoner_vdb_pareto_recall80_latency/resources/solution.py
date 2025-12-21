import numpy as np
import faiss
import time
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize IVF index optimized for latency with recall constraint.
        """
        self.dim = dim
        self.index = None
        self.xb = None
        self.xb_norm = None
        
        # IVF parameters optimized for latency while maintaining ~80% recall
        self.nlist = 8192  # Number of cells - higher means fewer vectors per cell
        self.nprobe = 2    # Number of cells to search - minimal for speed
        
        # Create quantizer and IVF index
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        # Enable parallelism for batch queries
        faiss.omp_set_num_threads(8)
        
        # Track if trained
        self.is_trained = False
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index with incremental training if needed.
        """
        if self.xb is None:
            self.xb = xb
        else:
            self.xb = np.vstack([self.xb, xb])
        
        # Train on subset if not trained yet
        if not self.is_trained:
            n_train = min(100000, len(self.xb))
            self.index.train(self.xb[:n_train])
            self.is_trained = True
        
        # Add all vectors
        if self.index.is_trained:
            self.index.add(self.xb)
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search with minimal nprobe for ultra-low latency.
        """
        # Set nprobe to minimal value for speed
        self.index.nprobe = self.nprobe
        
        # Pre-allocate for batch search
        nq = xq.shape[0]
        
        # Search with IVF
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
