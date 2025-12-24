import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Using HNSWFlat for optimal latency/recall tradeoff on SIFT1M.
        """
        self.dim = dim
        # M=32 provides a good balance of graph density for high recall
        self.index = faiss.IndexHNSWFlat(dim, 32)
        
        # Higher ef_construction creates a higher quality graph, 
        # allowing for faster search at a given recall level.
        # We have a generous build time budget (1 hr), so we maximize this.
        self.index.hnsw.efConstruction = 200
        
        # Ensure we use all available compute resources (8 vCPUs)
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss handles the graph construction internally
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # efSearch controls the recall/latency tradeoff during search.
        # For SIFT1M (1M vectors) + HNSW32:
        # - ef=40 typically yields ~96% recall
        # - ef=60 typically yields ~98% recall
        # We need strictly >= 0.95 recall.
        # We set efSearch=60 to provide a safety margin while remaining
        # well within the 7.7ms latency budget (expected < 1ms).
        self.index.hnsw.efSearch = 60
        
        return self.index.search(xq, k)
