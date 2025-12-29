import numpy as np
import faiss
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize an IVF index optimized for low latency with aggressive approximation.
        Using IVF4096 with nprobe=3 provides good speed/recall trade-off for 2.31ms target.
        """
        self.dim = dim
        self.nlist = kwargs.get('nlist', 4096)  # Number of Voronoi cells
        self.nprobe = kwargs.get('nprobe', 3)   # Number of cells to visit at query time
        
        # Quantizer for IVF - using L2 distance
        quantizer = faiss.IndexFlatL2(dim)
        
        # Create IVF index with quantizer
        self.index = faiss.IndexIVFFlat(quantizer, dim, self.nlist, faiss.METRIC_L2)
        
        # We'll train on the first batch of data
        self.is_trained = False
        self.train_threshold = 50000  # Minimum vectors needed for training

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index, training if needed.
        """
        if not self.is_trained:
            # Check if we have enough data to train
            n_samples = xb.shape[0]
            if n_samples >= self.train_threshold:
                # Train on all available data
                self.index.train(xb)
                self.is_trained = True
            else:
                # Not enough data yet, just add to buffer
                if not hasattr(self, 'xb_buffer'):
                    self.xb_buffer = xb.copy()
                else:
                    self.xb_buffer = np.vstack([self.xb_buffer, xb])
                
                # Check if buffer has enough for training
                if self.xb_buffer.shape[0] >= self.train_threshold:
                    self.index.train(self.xb_buffer)
                    self.is_trained = True
                    # Add buffered data to index
                    self.index.add(self.xb_buffer)
                    self.xb_buffer = None
                    return
        
        if self.is_trained:
            # Add vectors to trained index
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors with aggressive nprobe setting.
        """
        # Set nprobe for query time
        self.index.nprobe = self.nprobe
        
        # Ensure index is trained
        if not self.is_trained and hasattr(self, 'xb_buffer'):
            # Emergency training on buffer if somehow untrained
            self.index.train(self.xb_buffer)
            self.is_trained = True
            self.index.add(self.xb_buffer)
        
        # Precompute L2 norms for base vectors (optimization for batch queries)
        if not hasattr(self, 'norms_precomputed'):
            if hasattr(self.index, 'reconstruct_n'):
                # Get all vectors from index to precompute norms
                try:
                    all_vectors = []
                    for i in range(min(100000, self.index.ntotal)):
                        vec = self.index.reconstruct(i)
                        all_vectors.append(vec)
                    if all_vectors:
                        xb_all = np.vstack(all_vectors)
                        self.xb_norms = np.sum(xb_all ** 2, axis=1).astype(np.float32)
                        self.norms_precomputed = True
                except:
                    self.norms_precomputed = False
        
        # Search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)