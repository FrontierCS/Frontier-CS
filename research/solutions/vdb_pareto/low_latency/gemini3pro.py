import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        We use HNSW (Hierarchical Navigable Small World) graph index.
        HNSW offers an excellent trade-off between recall and latency.
        
        Configuration:
        - M=32: Number of connections per node. Higher M improves recall at cost of memory/speed.
          32 is a robust value for SIFT1M to achieve high recall.
        - IndexHNSWFlat: Stores full vectors (Flat) to compute exact distances for re-ranking
          candidates found via the graph. Fits in memory (1M * 128 * 4B = ~512MB).
        """
        self.dim = dim
        self.index = faiss.IndexHNSWFlat(dim, 32)
        
        # efConstruction controls the index build quality.
        # Higher value = better graph quality = faster convergence at query time.
        # Setting this high (200) improves recall/latency frontier.
        # Only affects build time, which is not strictly constrained (1h limit).
        self.index.hnsw.efConstruction = 200
        
        # Ensure FAISS uses all available CPU cores for batch processing.
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # FAISS requires C-contiguous float32 arrays
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # FAISS requires C-contiguous float32 arrays
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # efSearch controls the search depth (size of the dynamic candidate list).
        # We need to maximize recall while ensuring avg latency <= 2.31ms.
        # On 8 vCPUs, batch processing 10k queries with HNSW is very efficient.
        # efSearch=100 typically achieves >99% recall on SIFT1M while maintaining
        # latency well below the 2.31ms constraint (typically < 1.0ms/query in batch).
        self.index.hnsw.efSearch = 100
        
        # Perform search
        # D: Distances (L2 squared by default for IndexHNSWFlat, but actually 
        # FAISS returns L2 if metric is METRIC_L2. HNSWFlat defaults to L2.)
        D, I = self.index.search(xq, k)
        
        return D, I