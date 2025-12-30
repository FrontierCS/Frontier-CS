import numpy as np
import faiss
import os
from typing import Tuple

class HighRecallIndex:
    """
    An index for vector similarity search optimized for high recall,
    built using the Faiss library's HNSW implementation.

    This class is designed to meet the requirements of the VDB Design
    Problem's High Recall Tier. It prioritizes achieving a high recall@1
    score (>= 0.9914) within a relaxed latency constraint (<= 7.7ms).

    The strategy involves using a high-quality HNSW graph structure and
    performing a deep search at query time. The key parameters are:
    - M=64: Creates a dense and robust graph, improving connectivity and
      potential search paths.
    - efConstruction=512: A high value that ensures a well-structured graph
      is built, which is crucial for high-recall searches. This one-time
      cost during the `add` phase is acceptable.
    - efSearch=448: A high value for the search-time graph traversal. This
      parameter directly trades latency for recall. This value is chosen
      to be aggressive enough to surpass the recall baseline while staying
      within the generous latency budget, leveraging the 8 vCPUs of the
      evaluation environment for parallel processing of batch queries.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters for HNSW (M, efConstruction, efSearch).
        """
        self.dim = dim
        self.m = int(kwargs.get("M", 64))
        self.ef_construction = int(kwargs.get("efConstruction", 512))
        self.ef_search = int(kwargs.get("efSearch", 448))

        # Utilize all available CPU cores for Faiss operations.
        # The evaluation environment specifies 8 vCPUs.
        num_threads = os.cpu_count()
        if num_threads is not None:
            faiss.omp_set_num_threads(num_threads)

        # Initialize the HNSW index. IndexHNSWFlat uses L2 distance by default.
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Faiss requires float32 and C-contiguous arrays for optimal performance.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), L2 distances.
                - indices: shape (nq, k), indices of the nearest neighbors.
        """
        # Set the search-time parameter for HNSW.
        self.index.hnsw.efSearch = self.ef_search

        # Ensure query vectors are in the correct format for Faiss.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)

        distances, indices = self.index.search(xq, k)
        return distances, indices