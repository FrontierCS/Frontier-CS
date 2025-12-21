import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        optimized for SIFT1M with strict latency < 2.31ms.
        """
        self.dim = dim
        # HNSW configuration
        # M=32 provides good graph connectivity for high recall
        self.M = 32
        # ef_construction=200 ensures a high-quality graph structure (does not affect search latency)
        self.ef_construction = 200
        # ef_search=60 is tuned to maximize recall while safely staying under the 2.31ms latency limit
        # (Baseline 3.85ms typically corresponds to higher ef_search values)
        self.ef_search = 60
        
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Set the search-time parameter to enforce latency constraint
        self.index.hnsw.efSearch = self.ef_search
        return self.index.search(xq, k)
