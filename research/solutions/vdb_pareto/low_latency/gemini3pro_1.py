import numpy as np
import faiss
import time
from typing import Tuple

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Vector index optimized for low latency constraints.
        Uses HNSW with dynamic parameter tuning to maximize recall within the 2.31ms latency budget.
        """
        self.dim = dim
        # M=32 provides a good balance between graph connectivity and memory/speed
        self.M = 32
        # High ef_construction ensures a high-quality graph structure
        self.ef_construction = 200
        
        # Initialize Faiss HNSW Flat index
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.verbose = False

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss handles the addition and internal indexing
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors with auto-tuning for latency constraint.
        """
        nq = xq.shape[0]
        
        # Latency target in milliseconds
        # Constraint is 2.31ms. We target 2.0ms to provide a safety margin
        target_latency = 2.0
        
        # Dynamic Tuning Strategy
        # If the batch size is large enough, we run a probe on a subset of queries
        # to estimate the system performance and adjust efSearch accordingly.
        if nq >= 500:
            probe_size = 200
            probe_ef = 32
            
            # Set index to probe configuration
            self.index.hnsw.efSearch = probe_ef
            
            # Use a contiguous subset of queries for accurate timing
            xq_probe = np.ascontiguousarray(xq[:probe_size])
            
            # Measure execution time
            t0 = time.perf_counter()
            self.index.search(xq_probe, k)
            t1 = time.perf_counter()
            
            # Calculate average latency per query in ms
            elapsed_ms = (t1 - t0) * 1000.0
            avg_lat_probe = elapsed_ms / probe_size
            
            if avg_lat_probe > 0:
                # Estimate optimal efSearch assuming linear scaling between latency and efSearch
                # Apply a 0.95 factor for safety against non-linear overheads
                scale_factor = target_latency / avg_lat_probe
                optimal_ef = int(probe_ef * scale_factor * 0.95)
                
                # Clamp efSearch to reasonable bounds
                # min=10: Avoid extremely poor quality
                # max=200: Diminishing returns for recall vs latency risk
                self.index.hnsw.efSearch = max(10, min(optimal_ef, 200))
            else:
                # Fallback if timing measurement is unreliable (too fast)
                self.index.hnsw.efSearch = 64
        else:
            # Fallback for small batch sizes where tuning overhead is significant
            self.index.hnsw.efSearch = 48

        # Execute full search with tuned parameters
        return self.index.search(xq, k)