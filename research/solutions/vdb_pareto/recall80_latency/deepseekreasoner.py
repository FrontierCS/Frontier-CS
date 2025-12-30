import numpy as np
import faiss
import time
import heapq
from typing import Tuple

class Recall80LatencyTierIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Optimized for latency with recall >= 80% constraint.
        Uses IVF with minimal probes for extreme speed.
        """
        self.dim = dim
        
        # Extract parameters with optimized defaults for SIFT1M
        self.nlist = kwargs.get('nlist', 2048)  # Number of clusters
        self.nprobe = kwargs.get('nprobe', 3)   # Clusters to visit during search
        
        # Training configuration
        self.train_size = kwargs.get('train_size', 100000)  # Vectors for training
        
        # Initialize empty index
        self.index = None
        self.xb = None  # Store vectors for fallback or debugging
        self.is_trained = False
        
        # For batch search optimization
        self.batch_size = 10000  # Optimized for 10k queries
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index with training if needed.
        """
        if self.xb is None:
            self.xb = xb.copy()
        else:
            self.xb = np.vstack([self.xb, xb])
        
        # Train on subset if not trained yet
        if not self.is_trained:
            # Use a subset for training to save time
            train_data = xb[:min(self.train_size, len(xb))].copy()
            
            # Create IVF index
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            
            # Train with reasonable parameters
            self.index.train(train_data)
            self.is_trained = True
            
            # Add the training vectors
            self.index.add(train_data)
            
            # Add remaining vectors if any
            if len(xb) > self.train_size:
                self.index.add(xb[self.train_size:])
        else:
            # Just add to existing index
            self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fast batch search optimized for latency.
        Returns distances and indices for k nearest neighbors.
        """
        if self.index is None:
            # Fallback: exhaustive search (slow but accurate)
            return self._exhaustive_search(xq, k)
        
        # Configure search parameters for speed
        self.index.nprobe = self.nprobe
        
        # Pre-allocate output arrays
        nq = xq.shape[0]
        distances = np.empty((nq, k), dtype=np.float32)
        indices = np.empty((nq, k), dtype=np.int64)
        
        # Process in optimal batch size for cache efficiency
        batch_size = min(self.batch_size, nq)
        for start in range(0, nq, batch_size):
            end = min(start + batch_size, nq)
            batch_xq = xq[start:end]
            
            # Perform the actual search
            batch_dist, batch_idx = self.index.search(batch_xq, k)
            
            # Store results
            distances[start:end] = batch_dist
            indices[start:end] = batch_idx
        
        return distances, indices
    
    def _exhaustive_search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fallback exhaustive search (for debugging or when index not built).
        """
        nq = xq.shape[0]
        n = self.xb.shape[0]
        
        distances = np.empty((nq, k), dtype=np.float32)
        indices = np.empty((nq, k), dtype=np.int64)
        
        # Process in chunks to avoid memory issues
        chunk_size = 10000
        for start in range(0, n, chunk_size):
            end = min(start + chunk_size, n)
            xb_chunk = self.xb[start:end]
            
            # Compute squared L2 distances for this chunk
            for i in range(nq):
                diff = xb_chunk - xq[i]
                chunk_dists = np.sum(diff * diff, axis=1)
                
                # For each query, maintain top-k using heaps
                if start == 0:
                    # Initialize with first chunk
                    top_k = list(zip(chunk_dists, np.arange(start, end)))
                    heapq.heapify(top_k)
                else:
                    # Update with current chunk
                    for dist_val, idx in zip(chunk_dists, np.arange(start, end)):
                        if len(top_k) < k:
                            heapq.heappush(top_k, (-dist_val, idx))
                        elif -dist_val > top_k[0][0]:
                            heapq.heapreplace(top_k, (-dist_val, idx))
                
                # Store results
                if start + chunk_size >= n:
                    sorted_items = sorted(top_k, key=lambda x: -x[0])
                    distances[i] = [-d for d, _ in sorted_items]
                    indices[i] = [idx for _, idx in sorted_items]
        
        return distances, indices