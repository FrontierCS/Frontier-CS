import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A vector database index designed for the low-latency tier, prioritizing
    query speed while maintaining high recall. This implementation uses Faiss's
    IndexHNSWFlat, a state-of-the-art graph-based index for Approximate
    Nearest Neighbor (ANN) search on CPUs.

    The parameters are aggressively tuned to meet the strict latency constraint
    of 2.31ms per query on the SIFT1M dataset.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initializes the HNSW index.

        Args:
            dim: The dimensionality of the vectors.
            **kwargs: Optional parameters to override the defaults for HNSW.
                - M (int): Number of connections per node in the graph.
                           Default: 32.
                - efConstruction (int): Graph construction quality/speed tradeoff.
                                        Default: 400.
                - efSearch (int): Search-time quality/speed tradeoff. This is the
                                  most critical parameter for latency. Default: 48.
        """
        self.dim = dim

        # HNSW parameters are tuned for the low-latency requirement.
        # A higher M and efConstruction create a better graph, allowing for good
        # recall even with a low efSearch.
        self.M = int(kwargs.get('M', 32))
        self.efConstruction = int(kwargs.get('efConstruction', 400))
        
        # efSearch is set aggressively low to ensure latency is under the 2.31ms
        # threshold. This is the primary knob for controlling the speed vs.
        # recall trade-off.
        self.efSearch = int(kwargs.get('efSearch', 48))

        # IndexHNSWFlat stores full vectors, providing the best possible precision
        # for distance calculations, which helps maximize recall.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.efConstruction

        # Use faiss.ParameterSpace to set search-time parameters.
        self.params = faiss.ParameterSpace()
        self.params.set_index_parameter(self.index, "efSearch", self.efSearch)

    def add(self, xb: np.ndarray) -> None:
        """
        Adds vectors to the index. The HNSW graph is built incrementally.

        Args:
            xb: A numpy array of shape (N, dim) and dtype float32 containing
                the vectors to be added.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Performs a batch search for the k-nearest neighbors for each query vector.

        Args:
            xq: A numpy array of shape (nq, dim) and dtype float32 containing
                the query vectors.
            k: The number of nearest neighbors to retrieve for each query.

        Returns:
            A tuple (distances, indices):
                - distances: A (nq, k) numpy array of L2-squared distances.
                - indices: A (nq, k) numpy array of indices of the neighbors.
        """
        if self.index.ntotal == 0:
            # Handle search on an empty index to avoid runtime errors.
            nq = xq.shape[0]
            distances = np.full((nq, k), -1.0, dtype=np.float32)
            indices = np.full((nq, k), -1, dtype=np.int64)
            return distances, indices

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # The search is performed using the efSearch parameter set during init.
        distances, indices = self.index.search(xq, k, params=self.params)

        # Faiss with METRIC_L2 returns L2-squared distances, which is acceptable
        # and avoids the computational cost of a square root operation.
        return distances, indices