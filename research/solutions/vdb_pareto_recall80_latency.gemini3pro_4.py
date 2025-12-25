import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optimized for latency with a recall constraint of 0.80.
        Uses HNSW algorithm via Faiss.
        """
        self.dim = dim
        self.index = None
        self.ef_search = 32  # Default value, will be tuned in add()
        
        # HNSW Parameters
        # M=32 provides a good balance of connectivity and speed for SIFT1M
        self.M = 32
        # High ef_construction ensures a high-quality graph structure
        # This takes longer to build but improves search speed/recall trade-off
        self.ef_construction = 200
        
        # Initialize the index structure
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Optimize for the evaluation environment (8 vCPUs)
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index and tune search parameters.
        """
        # Add vectors to Faiss index
        self.index.add(xb)
        
        # Dynamic Tuning of efSearch
        # Goal: Find the minimum efSearch that satisfies the recall requirement.
        # Strategy: Use a subset of base vectors (xb) as queries to find themselves (reconstruction).
        # Finding "self" is a proxy for finding nearest neighbors. 
        # We target >99% self-recall to ensure >80% neighbor-recall.
        
        num_samples = min(2000, len(xb))
        # Randomly sample indices for calibration
        indices = np.random.choice(len(xb), num_samples, replace=False)
        xq_cal = xb[indices]
        
        best_ef = 32
        # Test a range of efSearch values, starting low to favor latency
        # 16 is typically the lower bound for usable recall on HNSW
        # 80 is a safe upper bound to stay under 0.6ms
        test_values = [16, 20, 24, 28, 32, 40, 48, 64, 80]
        
        for ef in test_values:
            self.index.hnsw.efSearch = ef
            # Search for k=1 (nearest neighbor)
            D, _ = self.index.search(xq_cal, 1)
            
            # Calculate self-recall: fraction of queries where distance to result is ~0
            # SIFT vectors are large, so 1e-4 is a safe threshold for float32 exact match
            recall_self = (D[:, 0] < 1e-4).mean()
            
            if recall_self > 0.99:
                best_ef = ef
                break
            best_ef = ef
            
        # Apply safety buffer
        # We increase the found ef slightly to account for the fact that finding neighbors 
        # is slightly harder than finding self.
        self.ef_search = int(best_ef * 1.2)
        
        # Apply strict bounds
        # Lower bound 16: to ensure stability
        # Upper bound 80: to ensure we don't violate the 0.6ms strict latency limit
        self.ef_search = max(16, min(self.ef_search, 80))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # efSearch must be at least k
        run_ef = max(self.ef_search, k)
        self.index.hnsw.efSearch = run_ef
        
        # Perform search using all available threads
        D, I = self.index.search(xq, k)
        return D, I
