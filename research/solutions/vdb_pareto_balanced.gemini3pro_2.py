import numpy as np
import faiss
import os
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Configuration optimized for SIFT1M to maximize recall within 5.775ms latency.
        """
        self.dim = dim
        
        # HNSW parameters
        # M=32 is a standard robust choice for SIFT1M (128d)
        # It provides excellent recall potential with manageable memory/compute
        self.M = 32
        
        # ef_construction=200 ensures a high-quality graph structure
        # Construction time is not part of the query latency constraint
        self.ef_construction = 200
        
        # Initialize HNSW index with Flat storage for exact distance calculations
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Configure Faiss to use all available cores (Evaluation env has 8 vCPUs)
        # Batch query performance scales linearly with threads
        try:
            n_threads = os.cpu_count() or 8
            faiss.omp_set_num_threads(n_threads)
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Tune search depth (efSearch)
        # Baseline recall (0.9914) is achieved at ~3.85ms.
        # Max allowed latency is 5.775ms (150% of baseline).
        # We select efSearch=150 to ensure we reliably exceed the baseline recall
        # while utilizing the extra latency budget safely.
        # Typical recall for M=32, ef=150 on SIFT1M is >0.993.
        self.index.hnsw.efSearch = 150
        
        D, I = self.index.search(xq, k)
        return D, I