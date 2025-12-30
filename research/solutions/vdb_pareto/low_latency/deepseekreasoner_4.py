import numpy as np
import faiss

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        We'll use IVF (Inverted File) with a small number of probes for very low latency.
        Based on the strict latency constraint (2.31ms), we need aggressive approximation.
        """
        self.dim = dim
        
        # Get parameters from kwargs or use defaults optimized for low latency
        self.nlist = kwargs.get('nlist', 256)  # Number of cells/centroids
        self.nprobe = kwargs.get('nprobe', 3)  # Very small for ultra-low latency
        self.quantizer_niter = kwargs.get('quantizer_niter', 20)  # k-means iterations
        
        # We'll use the IndexIVFFlat for fast search with low nprobe
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        # Set nprobe for search
        self.index.nprobe = self.nprobe
        
        # Track if index is trained
        self.is_trained = False
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        
        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # Train on a subset if we have many vectors (for speed)
            # For 1M vectors, train on 100k samples
            n_train = min(100000, len(xb))
            train_vectors = xb[:n_train].astype(np.float32)
            self.index.train(train_vectors)
            self.is_trained = True
        
        # Add all vectors
        self.index.add(xb.astype(np.float32))
        
    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors of query vectors.
        
        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return
            
        Returns:
            (distances, indices): Both as np.ndarray
        """
        xq_32 = xq.astype(np.float32)
        
        # Use batch processing for better cache locality
        # FAISS handles batch queries efficiently
        distances, indices = self.index.search(xq_32, k)
        
        return distances, indices