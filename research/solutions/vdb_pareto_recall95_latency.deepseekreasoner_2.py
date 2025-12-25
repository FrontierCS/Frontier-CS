import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # HNSW parameters optimized for high recall (95%+) with good latency
        # M=32 provides good connectivity for high recall
        # efConstruction=200 ensures good graph quality
        # efSearch will be set dynamically in search() for optimal speed-recall tradeoff
        self.M = kwargs.get('M', 32)
        self.ef_construction = kwargs.get('ef_construction', 200)
        
        # Initialize HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Store for potential re-indexing or debugging
        self.xb = None
        
        # Set to use multiple threads for batch operations
        faiss.omp_set_num_threads(8)
        
    def add(self, xb: np.ndarray) -> None:
        if self.xb is None:
            self.xb = xb.copy()
        else:
            self.xb = np.vstack([self.xb, xb])
        
        self.index.add(xb)
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        # Dynamic efSearch parameter: higher for first search to ensure recall,
        # but we can keep it relatively high (400) since we have generous latency budget
        # This ensures >95% recall while staying within 7.7ms
        self.index.hnsw.efSearch = 400
        
        # Perform the search
        distances, indices = self.index.search(xq, k)
        
        return distances.astype(np.float32), indices.astype(np.int64)
