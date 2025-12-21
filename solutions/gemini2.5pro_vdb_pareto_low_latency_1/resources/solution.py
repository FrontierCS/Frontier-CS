import numpy as np
import faiss
from typing import Tuple
import os

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW configuration:
                      - M: Number of neighbors per node (default: 32).
                      - ef_construction: Build-time beam size (default: 200).
                      - ef_search: Search-time beam size (default: 64).
        """
        try:
            num_threads = len(os.sched_getaffinity(0))
        except AttributeError:
            num_threads = os.cpu_count() or 1
        
        faiss.omp_set_num_threads(num_threads)

        self.dim = dim
        self.is_built = False

        # Parameters are tuned for the "Low Latency Tier". The goal is to maximize
        # recall under a very strict latency constraint (2.31ms).
        # We use FAISS's HNSW (Hierarchical Navigable Small World) implementation,
        # which provides an excellent speed-recall tradeoff on CPU.
        
        # `M`: Controls graph connectivity. A value of 32 is a common, robust choice.
        self.M = int(kwargs.get('M', 32))
        
        # `ef_construction`: Build-time parameter controlling graph quality.
        # A higher value leads to a better graph but longer build time. 200 is a solid default.
        self.ef_construction = int(kwargs.get('ef_construction', 200))
        
        # `ef_search`: The most critical search-time parameter. It controls the
        # size of the candidate pool during search. A smaller value is faster but
        # less accurate. We choose a relatively low value of 64 to aggressively
        # target the latency constraint.
        self.ef_search = int(kwargs.get('ef_search', 64))

        # We use IndexHNSWFlat, which stores uncompressed vectors. This helps maximize
        # recall, which is the scoring metric after the latency gate is passed.
        # The metric is L2, as required for the SIFT1M dataset.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. For HNSW, this process builds the graph.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        if xb.shape[1] != self.dim:
            raise ValueError(f"Input vector dimension {xb.shape[1]} does not match index dimension {self.dim}")

        self.index.add(xb)
        self.is_built = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), L2-squared distances.
                - indices: shape (nq, k), indices of the nearest neighbors.
        """
        if not self.is_built:
            raise RuntimeError("Index has not been built. Call add() first.")

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        if xq.shape[1] != self.dim:
            raise ValueError(f"Query vector dimension {xq.shape[1]} does not match index dimension {self.dim}")

        # Set the search-time parameter `efSearch`. This allows for dynamic
        # tuning of the speed/accuracy trade-off.
        self.index.hnsw.efSearch = self.ef_search
        
        distances, indices = self.index.search(xq, k)
        
        # FAISS's METRIC_L2 returns L2-squared distances. This is standard practice
        # as it preserves the ranking of neighbors and avoids a costly sqrt operation,
        # which is crucial for meeting the strict latency requirements.
        return distances, indices
