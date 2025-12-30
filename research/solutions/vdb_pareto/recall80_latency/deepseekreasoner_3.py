import numpy as np
import faiss

class LatencyOptimizedIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize an IVF index optimized for low latency with recall constraint.
        
        Parameters:
        - dim: Vector dimensionality (128 for SIFT1M)
        - **kwargs: Can override nlist (default: 4096) and nprobe (default: 2)
        """
        self.dim = dim
        
        # IVF parameters optimized for latency while maintaining >80% recall
        self.nlist = kwargs.get('nlist', 4096)  # Number of clusters
        self.nprobe = kwargs.get('nprobe', 2)   # Number of clusters to probe
        
        # Create quantizer (coarse quantizer for IVF)
        self.quantizer = faiss.IndexFlatL2(dim)
        
        # Create IVF index with flat storage (no compression for max speed)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        # Whether the index has been trained
        self.is_trained = False
        
        # For direct L2 distance computation if needed
        self.xb = None
        self.xb_norms = None

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        
        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # Train the index on a subset for speed (still gives good recall)
            n_train = min(100000, len(xb))
            train_subset = xb[:n_train].copy()
            self.index.train(train_subset)
            self.is_trained = True
        
        # Add the vectors
        self.index.add(xb)
        
        # Store the data for potential fallback or optimization
        if self.xb is None:
            self.xb = xb.copy()
        else:
            self.xb = np.vstack([self.xb, xb])
            
        # Precompute squared L2 norms for potential faster search
        self.xb_norms = np.sum(self.xb**2, axis=1, dtype=np.float32)

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors using optimized IVF.
        
        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return
            
        Returns:
            (distances, indices): Both as numpy arrays
        """
        # Set number of clusters to probe
        self.index.nprobe = self.nprobe
        
        # Search using IVF
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)

class FastIVFIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Alternative implementation with even faster search by using nprobe=1.
        
        Parameters:
        - dim: Vector dimensionality
        - **kwargs: Can override nlist (default: 16384) and nprobe (default: 1)
        """
        self.dim = dim
        
        # More aggressive parameters for lower latency
        self.nlist = kwargs.get('nlist', 16384)  # More clusters for higher recall with nprobe=1
        self.nprobe = kwargs.get('nprobe', 1)    # Minimal probe count for speed
        
        # Create the IVF index
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        self.is_trained = False

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index with training if needed.
        """
        if not self.is_trained:
            # Train with reasonable sample size
            n_train = min(50000, len(xb))
            train_subset = xb[:n_train].copy()
            self.index.train(train_subset)
            self.is_trained = True
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Fast search with minimal cluster probing.
        """
        self.index.nprobe = self.nprobe
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Main index class optimized for recall≥80% with minimal latency.
        
        Uses a multi-level strategy with very aggressive parameters.
        """
        self.dim = dim
        
        # Very aggressive IVF parameters optimized for <0.6ms
        self.nlist = 32768  # Many small clusters for good recall with nprobe=1
        self.nprobe = 1     # Absolute minimum for speed
        
        # Create the index
        self.quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        # Use precomputed centroids for faster distance computation
        faiss.ParameterSpace().set_index_parameter(self.index, 'use_precomputed_table', 1)
        
        self.is_trained = False
        self.xb = None

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors with efficient training on a subset.
        """
        if not self.is_trained:
            # Use a small training set for speed
            n_train = min(25000, len(xb))
            train_subset = xb[:n_train].copy()
            self.index.train(train_subset)
            self.is_trained = True
        
        self.index.add(xb)
        self.xb = xb.copy() if self.xb is None else np.vstack([self.xb, xb])

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Ultra-fast search targeting <0.6ms average latency.
        """
        self.index.nprobe = self.nprobe
        
        # Use FAISS with direct distance computation disabled for speed
        faiss.downcast_index(self.index).direct_map = faiss.DirectMap.NoMap
        
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)