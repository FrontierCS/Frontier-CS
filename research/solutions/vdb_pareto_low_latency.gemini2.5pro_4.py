import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        This index is optimized for the low latency tier by using Faiss's HNSW
        implementation. HNSW (Hierarchical Navigable Small World) is a graph-based
        index that provides an excellent speed/recall trade-off, which is ideal
        for maximizing recall under a strict latency constraint.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW configuration.
        """
        self.dim = dim
        self.index = None

        # --- Tuned HNSW Parameters for Low Latency Tier ---
        # These parameters are chosen to provide a balance between build time,
        # memory usage, and the critical search speed vs. recall trade-off.

        # M: Number of neighbors per node in the graph. A higher M creates a
        # denser graph, improving recall at the cost of memory and build time.
        # 32 is a standard value providing a good balance.
        M = kwargs.get("M", 32)

        # efConstruction: A build-time parameter that affects the quality of the
        # HNSW graph. A higher value leads to a better graph structure, which
        # can improve search performance and recall.
        ef_construction = kwargs.get("ef_construction", 120)

        # efSearch: The key query-time parameter. It controls the size of the
        # dynamic list of candidates during the search. A lower value is faster
        # but yields lower recall. This value is set aggressively to meet the
        # < 2.31ms latency target while maximizing recall.
        self.ef_search = kwargs.get("ef_search", 64)

        # We use IndexHNSWFlat which stores the full, uncompressed vectors.
        # This maximizes recall, and its memory footprint (~768MB for SIFT1M)
        # is well within the 16GB RAM limit of the evaluation environment.
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # HNSW does not require a separate training step. Faiss parallelizes
        # the `add` operation across available CPU cores.
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        # Set the search-time parameter `efSearch` for the HNSW algorithm.
        self.index.hnsw.efSearch = self.ef_search

        # Faiss's search is highly optimized for batch queries and will
        # efficiently use multi-core CPUs.
        distances, indices = self.index.search(xq, k)

        return distances, indices
