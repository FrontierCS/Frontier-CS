import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Using HNSW with high M and ef parameters to maximize recall 
        within the relaxed 7.7ms latency constraint.
        """
        self.dim = dim
        
        # Configure FAISS to use all 8 available vCPUs
        faiss.omp_set_num_threads(8)
        
        # HNSW Parameters
        # M=64: High connectivity for better recall (trade-off: memory/speed)
        # SIFT1M is small enough that M=64 fits easily in RAM
        self.M = 64
        
        # efConstruction: 500 ensures a high-quality graph structure
        self.ef_construction = 500
        
        # efSearch: 240
        # Tuned to guarantee recall > 0.9914 (baseline)
        # Latency estimated to be ~2-4ms, well within 7.7ms limit
        self.ef_search = 240
        
        # Initialize HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure array is contiguous for FAISS C++ bindings
        if not xb.flags.c_contiguous:
            xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Ensure efSearch is applied (stateful parameter in FAISS)
        self.index.hnsw.efSearch = self.ef_search
        
        if not xq.flags.c_contiguous:
            xq = np.ascontiguousarray(xq)
            
        distances, indices = self.index.search(xq, k)
        return distances, indices