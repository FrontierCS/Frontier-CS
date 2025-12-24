import numpy as np
import faiss
from typing import Tuple

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Strategy:
        - Use HNSW (Hierarchical Navigable Small World) graph for efficient ANN search.
        - Set M=64 (number of neighbors per node) to create a denser graph than standard (usually 32).
          This improves recall capability at the cost of slightly higher memory and latency.
        - Set efConstruction=500 to build a high-quality graph. Build time is not part of the score
          (subject to 1h timeout), so we optimize for graph quality.
        - Configure OpenMP to utilize all 8 vCPUs for parallel batch search.
        """
        self.dim = dim
        # M=64 gives high connectivity, crucial for high recall
        self.index = faiss.IndexHNSWFlat(dim, 64)
        
        # High construction effort for better graph navigation
        self.index.hnsw.efConstruction = 500
        
        # Ensure FAISS uses all available CPU cores
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        
        Strategy:
        - The latency constraint is 7.7ms (relaxed compared to 3.85ms baseline).
        - We can afford a deeper search to ensure we meet or exceed the 0.9914 recall baseline.
        - efSearch=320 with M=64 typically yields >99.5% recall on SIFT1M while maintaining
          latency in the 3-5ms range on modern CPUs, safely within the 7.7ms limit.
        """
        # Set search depth
        self.index.hnsw.efSearch = 320
        
        # Perform search (returns distances and indices)
        return self.index.search(xq, k)
