import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        We use HNSW (Hierarchical Navigable Small World) index which offers 
        state-of-the-art performance for recall/latency trade-offs.
        Given the relaxed latency constraint (7.7ms) and high recall requirement,
        we tune parameters aggressively for accuracy.
        """
        self.dim = dim
        
        # HNSW Parameters
        # M=64: Higher number of edges per node increases graph connectivity and recall,
        # at the cost of memory and slightly higher search time (well within 7.7ms budget).
        M = 64
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        
        # efConstruction=512: Controls index build quality. Higher values lead to 
        # a better graph structure, improving recall. Since index build time is not
        # strictly constrained (1 hour timeout), we maximize this.
        self.index.hnsw.efConstruction = 512
        
        # Utilize all 8 vCPUs for batch processing
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss expects float32 and C-contiguous memory layout
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Faiss expects float32 and C-contiguous memory layout
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq)
            
        # Search Parameter Tuning
        # efSearch: Controls the size of the dynamic candidate list during search.
        # Higher efSearch -> Higher Recall, Higher Latency.
        #
        # Analysis:
        # - Target Recall: > 0.9914
        # - Max Latency: 7.7ms
        # - HNSW (M=64) on SIFT1M with 8 vCPUs typically achieves < 1.0ms latency 
        #   even with very high efSearch settings.
        # 
        # We select efSearch=512 to virtually guarantee recall > 0.9914 (often > 0.998)
        # while staying safely under the 7.7ms limit.
        self.index.hnsw.efSearch = 512
        
        # Perform search
        # Returns (distances, indices) tuple
        return self.index.search(xq, k)