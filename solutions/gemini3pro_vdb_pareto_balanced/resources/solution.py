import numpy as np
import faiss
from typing import Tuple

class BalancedIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Strategy:
        - Use HNSW (Hierarchical Navigable Small World) graph for high recall and low latency.
        - M=32 provides a dense enough graph for high recall on SIFT1M.
        - efConstruction=200 ensures a high-quality graph is built.
        - efSearch is tuned to meet the recall@1 > 0.9914 requirement while staying under 5.775ms.
        """
        self.dim = dim
        
        # HNSW Parameters
        # M: Number of connections per node. 32 is robust for SIFT1M.
        self.M = 32
        # efConstruction: Controls index quality/build time. 200 is high quality.
        self.ef_construction = 200
        # efSearch: Controls recall/latency trade-off. 
        # 160 is chosen to safely exceed 0.9914 recall while leveraging 8 vCPUs to stay < 5ms.
        self.ef_search_base = 160
        
        # Initialize FAISS IndexHNSWFlat
        # Uses L2 distance (METRIC_L2)
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Configure parallelism
        # Explicitly set to 8 threads to utilize the evaluation environment limits
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # FAISS requires float32 input
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # FAISS requires float32 input
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set efSearch for this query batch
        # Ensure we search at least k nodes, but default to our tuned high-recall value
        self.index.hnsw.efSearch = max(self.ef_search_base, k)
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
