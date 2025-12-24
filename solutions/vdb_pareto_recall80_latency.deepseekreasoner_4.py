import numpy as np
import faiss
import time
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.nlist = kwargs.get('nlist', 2048)
        self.nprobe = kwargs.get('nprobe', 2)
        self.quantizer = None
        self.index = None
        self.trained = False
        
    def add(self, xb: np.ndarray) -> None:
        if self.index is None:
            # Use IVF index for fast approximate search
            self.quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            
            # Train on first 100k samples for speed
            n_train = min(100000, xb.shape[0])
            train_data = xb[:n_train].copy()
            self.index.train(train_data)
            self.trained = True
            
        if self.trained:
            self.index.add(xb)
        else:
            # If not trained yet, add to buffer and train later
            if not hasattr(self, 'xb_buffer'):
                self.xb_buffer = []
            self.xb_buffer.append(xb.copy())
            
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not self.trained and hasattr(self, 'xb_buffer'):
            # Train on buffered data
            all_buffered = np.vstack(self.xb_buffer)
            n_train = min(100000, all_buffered.shape[0])
            train_data = all_buffered[:n_train]
            self.index.train(train_data)
            self.index.add(all_buffered)
            self.trained = True
            del self.xb_buffer
            
        self.index.nprobe = self.nprobe
        
        # Search with minimal parameters for maximum speed
        D, I = self.index.search(xq, k)
        
        # Compute actual L2 distances for accuracy
        if hasattr(self, 'xb_stored'):
            xb = self.xb_stored
        else:
            # Get vectors from index
            xb = np.vstack([self.index.reconstruct(i) for i in range(self.index.ntotal)])
            self.xb_stored = xb
            
        # Compute exact distances for the top candidates
        nq = xq.shape[0]
        exact_distances = np.zeros((nq, k), dtype=np.float32)
        
        for i in range(nq):
            for j in range(k):
                idx = I[i, j]
                if idx >= 0:
                    exact_distances[i, j] = np.sum((xq[i] - xb[idx]) ** 2)
                else:
                    exact_distances[i, j] = float('inf')
                    
        return exact_distances, I
