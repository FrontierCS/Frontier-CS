import numpy as np
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize IVF index with aggressive parameters for low latency.
        Use very small nprobe (2-3) to meet strict 2.31ms constraint.
        """
        self.dim = dim
        self.nlist = kwargs.get('nlist', 1024)  # Number of Voronoi cells
        self.nprobe = kwargs.get('nprobe', 3)   # Very aggressive for low latency
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe
        self.trained = False
        self.xb = None  # Store for incremental adds if needed
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors with incremental training on first batch.
        """
        if self.xb is None:
            self.xb = xb
        else:
            self.xb = np.vstack([self.xb, xb])
            
        if not self.trained:
            # Train on a subset for efficiency
            n_train = min(50000, len(xb))
            self.index.train(xb[:n_train].astype(np.float32))
            self.trained = True
            
        self.index.add(xb.astype(np.float32))
        
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Batch search with very low nprobe for minimal latency.
        Returns L2 distances and indices.
        """
        xq = xq.astype(np.float32)
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)