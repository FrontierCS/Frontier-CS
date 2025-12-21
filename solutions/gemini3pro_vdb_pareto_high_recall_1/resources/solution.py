import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Strategy:
        - Use Faiss IndexHNSWFlat for high recall and efficient search.
        - Increase M (edges per node) to 64 to improve graph connectivity and recall.
        - Increase ef_construction to 500 to build a high-quality graph.
        - Set ef_search to 800 to maximize recall within the relaxed 7.7ms latency budget.
          With 8 vCPUs and batch processing, this setting stays well below the latency limit
          while ensuring recall > 0.9914.
        """
        self.dim = dim
        
        # HNSW parameters
        # M=64 gives higher accuracy than standard 32
        self.M = 64
        # Higher construction depth for better graph quality
        self.ef_construction = 500
        # High search depth to ensure we hit the recall target
        self.ef_search = 800
        
        # Create the index
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors using the configured HNSW index.
        """
        # Set the search parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        # Faiss automatically utilizes available CPU cores (OpenMP) for batch queries
        D, I = self.index.search(xq, k)
        
        return D, I
