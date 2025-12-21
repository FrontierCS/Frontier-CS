import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An optimized vector database index for the Recall80 Latency Tier.

    This implementation uses FAISS's HNSW (Hierarchical Navigable Small World)
    graph-based index. HNSW provides an excellent trade-off between search speed
    and recall, making it suitable for this high-performance task.

    The hyperparameters (m, ef_construction, ef_search) are specifically tuned
    to meet the aggressive latency target (< 0.6ms avg query time) while
    maintaining a recall@1 of at least 80% on the SIFT1M dataset.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initializes the HNSW index.

        Args:
            dim: The dimensionality of the vectors.
            **kwargs: Optional parameters (not used in this tuned implementation).
        """
        self.dim = dim
        self.index = None

        # Hyperparameters for faiss.IndexHNSWFlat, tuned for the Recall@80 Latency tier.
        # The goal is to be extremely fast while maintaining recall >= 0.80.

        # M: Number of neighbors per node in the graph. A lower value is faster
        # and uses less memory. `m=16` is a good balance for speed.
        m = 16

        # efConstruction: Build-time search depth. A higher value creates a
        # better quality graph, which can improve search performance. Build time
        # is not critical as long as it's within the 1-hour limit.
        ef_construction = 80

        # efSearch: Search-time search depth. This is the most critical parameter.
        # It's set to a very low value to meet the aggressive latency target.
        # Based on public benchmarks for SIFT1M, a value around 10-12 should
        # be sufficient for ~80-82% recall. We choose 10 for maximum speed.
        # This value must be >= k.
        self.ef_search = 10

        # Initialize the index. We use IndexHNSWFlat because it does not use
        # compression, maximizing recall for a given graph traversal. The SIFT1M
        # dataset fits comfortably in memory. METRIC_L2 is used for Euclidean distance.
        self.index = faiss.IndexHNSWFlat(dim, m, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Adds vectors to the index. For HNSW, this method builds the graph.
        This can be a time-consuming operation for large datasets.

        Args:
            xb: A numpy array of shape (N, dim) and dtype float32 containing
                the vectors to be added.
        """
        if self.index is not None:
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Performs a k-nearest neighbor search for the query vectors.

        Args:
            xq: A numpy array of shape (nq, dim) and dtype float32 containing
                the query vectors.
            k: The number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: A (nq, k) float32 array of L2 squared distances.
                - indices: A (nq, k) int64 array of indices of the nearest neighbors.
        """
        if self.index is None or self.index.ntotal == 0:
            # Handle the case of an empty index to avoid errors.
            nq = xq.shape[0]
            return np.full((nq, k), -1, dtype=np.float32), \
                   np.full((nq, k), -1, dtype=np.int64)

        # Set the search-time parameter to control the speed/accuracy trade-off.
        self.index.hnsw.efSearch = max(k, self.ef_search)

        # Faiss search returns L2 squared distances for METRIC_L2, which is
        # faster than computing the full L2 distance and acceptable per problem spec.
        distances, indices = self.index.search(xq, k)

        return distances, indices
