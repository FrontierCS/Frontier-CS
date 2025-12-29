import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Using HNSW (Hierarchical Navigable Small World) index for high recall and low latency.
        """
        self.dim = dim
        
        # HNSW configuration
        # M: Number of connections per node in the graph. 
        # M=32 is a robust sweet spot for 128-dim vectors (SIFT1M), 
        # offering a good balance between recall and speed.
        self.M = 32
        
        # Create HNSW index with Flat storage (exact distances)
        # We do not use Product Quantization (PQ) as it reduces recall, 
        # and we have sufficient memory (16GB) for 1M float32 vectors.
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # Construction parameter: ef_construction
        # A higher value creates a higher quality graph (better connections),
        # which improves search speed/recall trade-off at the cost of build time.
        # 200 is a safe high value.
        self.index.hnsw.efConstruction = 200
        
        # Search parameter: ef_search
        # Controls the size of the dynamic candidate list during search.
        # This is the primary knob for Latency vs Recall.
        # Based on SIFT1M characteristics:
        # ef=64 typically guarantees Recall@1 > 0.98, safely above the 0.95 gate,
        # while maintaining latency well below the 7.7ms limit (typically < 2ms on modern CPUs).
        self.default_ef_search = 64
        self.index.hnsw.efSearch = self.default_ef_search
        
        # Optimize for the evaluation environment (8 vCPUs)
        # Explicitly setting threads ensures we utilize full compute for batch queries.
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss requires float32 and C-contiguous memory
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Prepare query vectors
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
            
        # Dynamically adjust efSearch to be at least k
        # HNSW requires efSearch >= k to return k unique results.
        # We maximize with our tuned default to ensure recall constraints are met.
        current_ef = max(self.default_ef_search, k)
        self.index.hnsw.efSearch = current_ef
        
        # Perform search
        D, I = self.index.search(xq, k)
        
        return D, I