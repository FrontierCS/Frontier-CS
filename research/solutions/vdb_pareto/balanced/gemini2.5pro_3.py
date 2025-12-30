import numpy as np
from typing import Tuple
import faiss
import os

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction for HNSW)
        """
        # Utilize all available CPU cores for parallel processing during search.
        # This is critical for meeting the latency constraint with batch queries.
        if hasattr(faiss, "omp_set_num_threads"):
            num_threads = os.cpu_count()
            if num_threads is not None:
                faiss.omp_set_num_threads(num_threads)

        self.dim = dim
        self.index = None

        # --- Parameter Tuning for HNSW (Hierarchical Navigable Small World) ---
        # The goal is to maximize recall@1 under the 5.775ms latency constraint.
        # This requires a high-quality index and an exhaustive search.

        # M: Number of neighbors per node. Higher values create a denser, more
        # accurate graph, improving recall at the cost of memory and build time.
        # M=48 is a strong choice for high-recall scenarios.
        M = 48
        
        # efConstruction: Controls index quality during the build phase. Higher
        # values lead to better search performance. Given the generous build time
        # allowance, we can set this high to create an optimal graph structure.
        efConstruction = 512
        
        # efSearch: Controls the search-time trade-off between speed and recall.
        # This is the most critical parameter. We set it to an aggressive value
        # to use as much of the latency budget as possible to find the true
        # nearest neighbors, thus maximizing recall. This value is chosen based on
        # balancing the risk of exceeding the latency gate against the reward of higher recall.
        self.efSearch = 144

        # We use IndexHNSWFlat, which stores the original, uncompressed vectors.
        # This avoids the recall degradation associated with quantization methods (like PQ)
        # and is necessary for achieving recalls above 99%.
        # The metric is set to L2, as required by the SIFT1M dataset.
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = efConstruction
        self.index.hnsw.efSearch = self.efSearch


    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32

        Notes:
            - Can be called multiple times (cumulative)
            - Must handle large N (e.g., 1,000,000 vectors)
        """
        # HNSW indices do not require a separate training step.
        # We can add vectors directly. FAISS handles cumulative adds.
        if xb.shape[0] > 0:
            self.index.add(xb)


    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances
                - indices: shape (nq, k), dtype int64, indices into base vectors

        Notes:
            - Must return exactly k neighbors per query
            - Indices should refer to positions in the vectors passed to add()
            - Lower distance = more similar
        """
        # Handle the edge case of an empty index.
        if self.index.ntotal == 0:
            return (
                np.full((xq.shape[0], k), -1.0, dtype=np.float32),
                np.full((xq.shape[0], k), -1, dtype=np.int64),
            )

        # The efSearch parameter, which dictates search quality, is set during
        # initialization. The search method will use this pre-configured value.
        distances, indices = self.index.search(xq, k)
        
        # The problem allows for L2 or L2-squared distances. Faiss's METRIC_L2
        # returns squared distances, which is faster as it avoids a sqrt operation
        # for every returned distance. We return these directly for maximum performance.
        return distances, indices