import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Configuration optimized for SIFT1M recall@1 > 0.9914 within strict latency.
        """
        self.dim = dim
        
        # HNSW parameters tuned for the trade-off
        # M=32 provides robust graph connectivity for high recall
        self.M = 32
        # ef_construction=128 ensures high quality graph during build
        self.ef_construction = 128
        # ef_search=96 is sufficient for >0.99 recall while keeping latency < 1ms in batch
        self.ef_search = 96
        
        # Use HNSW with Flat storage (no quantization) for maximum recall
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Ensure we utilize all available vCPUs for batch processing
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Set the search depth
        self.index.hnsw.efSearch = self.ef_search
        
        # Faiss search returns (distances, indices) matching the requirement
        D, I = self.index.search(xq, k)
        return D, I