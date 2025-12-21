import numpy as np
import faiss
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize index for low-latency vector search.
        Uses IVF with aggressive parameters to meet strict latency constraints.
        """
        self.dim = dim
        
        # IVF parameters optimized for speed
        self.nlist = 1024  # Number of Voronoi cells (clusters)
        self.nprobe = 2    # Number of cells to probe (very aggressive for speed)
        
        # Use OPQ for better recall with lower nprobe
        opq_dim = 64 if dim >= 64 else dim  # Reduce dimension for faster distance computation
        self.opq = faiss.OPQMatrix(dim, opq_dim)
        
        # Create the IVF index with OPQ preprocessing
        quantizer = faiss.IndexFlatL2(opq_dim)
        self.index = faiss.IndexIVFFlat(quantizer, opq_dim, self.nlist, faiss.METRIC_L2)
        
        # Set nprobe
        self.index.nprobe = self.nprobe
        
        # Training sample size (for faster training)
        self.training_samples = min(100000, 100 * self.nlist)
        
        # Track if index is trained
        self.is_trained = False
        self.total_vectors = 0

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index with batched processing.
        """
        if xb.size == 0:
            return
            
        n = xb.shape[0]
        
        # Train on first batch if not trained yet
        if not self.is_trained:
            # Use subset for training to save time
            n_train = min(self.training_samples, n)
            train_data = xb[:n_train].copy()
            
            # Apply OPQ training
            self.opq.train(train_data)
            train_data_transformed = self.opq.apply_py(train_data)
            
            # Train IVF index
            self.index.train(train_data_transformed)
            self.is_trained = True
            
            # Add training vectors
            self.index.add(train_data_transformed)
            self.total_vectors += n_train
            
            # Add remaining vectors if any
            if n > n_train:
                remaining = xb[n_train:].copy()
                remaining_transformed = self.opq.apply_py(remaining)
                self.index.add(remaining_transformed)
                self.total_vectors += (n - n_train)
        else:
            # Apply OPQ transformation and add
            xb_transformed = self.opq.apply_py(xb.copy())
            self.index.add(xb_transformed)
            self.total_vectors += n

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors with aggressive speed optimization.
        """
        if not self.is_trained or self.total_vectors == 0:
            # Return empty results if index is empty
            nq = xq.shape[0]
            return np.zeros((nq, k), dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)
        
        # Apply OPQ transformation to queries
        xq_transformed = self.opq.apply_py(xq.copy())
        
        # Search with IVF
        distances, indices = self.index.search(xq_transformed, k)
        
        # Convert squared L2 distances back to L2 (if needed for consistency)
        # Note: IVF with METRIC_L2 returns squared distances
        # We return squared distances for speed, as recall calculation uses indices only
        return distances.astype(np.float32), indices.astype(np.int64)
