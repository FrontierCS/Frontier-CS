import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index for high recall within latency constraints.
        
        Parameters tuned for SIFT1M dataset (1M vectors, 128 dim) to achieve:
        - Recall >= baseline (0.9914)
        - Latency <= 5.775ms (batch of 10K queries)
        """
        self.dim = dim
        
        # HNSW parameters optimized for recall with acceptable latency
        # Higher M (neighbors) and ef_search improve recall at cost of speed
        M = kwargs.get('M', 32)  # Increased from default 16 for better recall
        ef_construction = kwargs.get('ef_construction', 400)  # High for accuracy
        self.ef_search = kwargs.get('ef_search', 128)  # High for recall, but not too high for latency
        
        # Create HNSW index
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Store vectors for distance computation if needed
        self.vectors = None
        
        # For batch query optimization
        self.batch_size = 10000  # Match typical evaluation batch size

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        
        HNSW supports incremental addition.
        """
        if self.vectors is None:
            self.vectors = xb.copy()
        else:
            self.vectors = np.vstack([self.vectors, xb])
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        
        Optimized for batch queries (10K queries at once).
        HNSW provides good recall with controlled latency.
        """
        # Ensure efSearch is set
        self.index.hnsw.efSearch = self.ef_search
        
        # Search in batches if needed (though 10K is reasonable)
        if len(xq) <= self.batch_size:
            distances, indices = self.index.search(xq, k)
        else:
            # Process in batches (though typically not needed for 10K queries)
            distances_list = []
            indices_list = []
            for i in range(0, len(xq), self.batch_size):
                batch_xq = xq[i:i + self.batch_size]
                batch_distances, batch_indices = self.index.search(batch_xq, k)
                distances_list.append(batch_distances)
                indices_list.append(batch_indices)
            
            distances = np.vstack(distances_list)
            indices = np.vstack(indices_list)
        
        return distances.astype(np.float32), indices.astype(np.int64)
