import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        
        # These parameters are tuned to maximize recall for the SIFT1M dataset 
        # while staying comfortably under the 5.775ms latency constraint on 
        # an 8-vCPU environment. HNSW is selected for its state-of-the-art
        # performance in high-recall regimes.
        self.M = kwargs.get('M', 48)
        self.ef_construction = kwargs.get('ef_construction', 400)
        self.ef_search = kwargs.get('ef_search', 1536)
        
        # IndexHNSWFlat stores full vectors, which is ideal for achieving high
        # recall without precision loss from quantization.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

        # Set the number of threads to utilize all available CPUs.
        num_threads = kwargs.get('num_threads', 8)
        faiss.omp_set_num_threads(num_threads)
        
    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time quality/speed trade-off parameter.
        self.index.hnsw.efSearch = self.ef_search

        # Faiss with METRIC_L2 returns squared L2 distances, which is acceptable.
        distances, indices = self.index.search(xq, k)

        return distances, indices