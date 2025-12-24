import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for low latency.
        Using very aggressive parameters to meet 2.31ms constraint.
        """
        self.dim = dim
        
        # HNSW parameters optimized for latency-constrained recall
        # M=16: lower connectivity for faster traversal (default 32)
        # efConstruction=100: moderate construction for decent recall
        # efSearch=64: aggressive search parameter for low latency
        M = kwargs.get('M', 16)
        ef_construction = kwargs.get('ef_construction', 100)
        ef_search = kwargs.get('ef_search', 64)
        
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        
        # Store for batch optimization
        self.vectors_added = 0
        
    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index in batches for efficiency.
        """
        batch_size = 10000  # Reasonable batch size for memory efficiency
        n = xb.shape[0]
        
        for i in range(0, n, batch_size):
            end_idx = min(i + batch_size, n)
            batch = xb[i:end_idx]
            self.index.add(batch)
        
        self.vectors_added += n
        
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search using HNSW with aggressive parameters for low latency.
        Batch queries benefit from CPU vectorization.
        """
        # Ensure k doesn't exceed number of vectors
        k = min(k, self.vectors_added)
        
        # Perform the search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
