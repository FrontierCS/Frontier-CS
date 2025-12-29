import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A FAISS-based HNSW index optimized for the Recall95 Latency Tier.

    This index uses the Hierarchical Navigable Small World (HNSW) algorithm,
    which is a state-of-the-art graph-based method for approximate nearest
    neighbor search. It is particularly effective for high-recall scenarios on
    CPU, which aligns with the problem's requirements.

    Key design choices:
    1.  **Index Type**: `faiss.IndexHNSWFlat`. The "Flat" suffix indicates that
        the full, original vectors are stored in the index. This avoids any
        quantization-related accuracy loss, making it easier to achieve the
        high 95% recall target. The metric is set to L2 Euclidean distance.

    2.  **Parameter Tuning**: The HNSW parameters are chosen based on
        well-established benchmarks for the SIFT1M dataset to provide a balance
        of high recall and low latency.
        -   `M=32`: The number of neighbors for each node in the graph. This is a
            standard value that provides a good trade-off between memory usage,
            build time, and search performance.
        -   `efConstruction=200`: A build-time parameter that controls the quality
            of the graph. A higher value leads to a better index and improved
            recall, at the cost of a longer build time. The generous 1-hour
            build limit allows for a high-quality construction.
        -   `efSearch=80`: A search-time parameter that controls the breadth of
            the search. This value is carefully selected to comfortably exceed the
            95% recall gate (expected recall ~97-98%) while remaining very fast,
            thereby maximizing the latency score.

    3.  **Parallelization**: The implementation leverages the 8 vCPUs available
        in the evaluation environment by setting `faiss.omp_set_num_threads(8)`.
        This dramatically speeds up both index construction and, more importantly,
        batch search operations.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M).
            **kwargs: Optional parameters to override defaults.
                - M: HNSW connectivity (default: 32).
                - ef_construction: HNSW build-time quality (default: 200).
                - ef_search: HNSW search-time quality (default: 80).
                - num_threads: Number of CPU threads to use (default: 8).
        """
        self.dim = dim
        self.M = kwargs.get("M", 32)
        self.ef_construction = kwargs.get("ef_construction", 200)
        self.ef_search = kwargs.get("ef_search", 80)

        # Initialize the HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

        # Configure Faiss to use multiple threads for parallel execution
        self.num_threads = kwargs.get("num_threads", 8)
        faiss.omp_set_num_threads(self.num_threads)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Faiss requires float32 input
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
            - distances: shape (nq, k), float32, L2-squared distances.
            - indices: shape (nq, k), int64, indices of nearest neighbors.
        """
        # Set the search-time exploration factor
        self.index.hnsw.efSearch = self.ef_search

        # Faiss requires float32 input
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Perform the search
        distances, indices = self.index.search(xq, k)

        return distances, indices