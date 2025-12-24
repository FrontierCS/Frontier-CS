import numpy as np
import faiss
from typing import Tuple, Optional

class YourIndexClass:
    """
    A FAISS-based high-recall index using Hierarchical Navigable Small World (HNSW).

    This index is optimized for high recall@1, leveraging the relaxed latency
    constraint provided in the problem. It uses HNSW with aggressive search
    parameters (efSearch) to perform a more thorough search of the vector space,
    trading higher latency for improved accuracy. The construction parameters
    (M, efConstruction) are also set high to build a high-quality graph structure,
    further enhancing search performance at the cost of a longer, one-time build.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters for HNSW.
                M (int): Number of neighbors per node in the HNSW graph. Defaults to 64.
                ef_construction (int): Search depth during index construction. Defaults to 512.
                ef_search (int): Search depth during queries. Defaults to 800.
        """
        self.dim = dim
        self.is_trained = False

        # HNSW parameters tuned for high recall. The relaxed latency budget
        # allows for more aggressive (i.e., higher) values.
        # - M: Higher M increases memory but creates a more robust graph.
        # - ef_construction: Higher value creates a higher-quality graph.
        # - ef_search: The key parameter. Higher value increases search time
        #   but significantly improves recall by exploring more of the graph.
        m = kwargs.get("M", 64)
        ef_construction = kwargs.get("ef_construction", 512)
        self.ef_search = kwargs.get("ef_search", 800)

        # Using IndexHNSWFlat which stores the full vectors. This avoids
        # quantization errors from methods like PQ, ensuring perfect distance
        # calculations for retrieved vectors, which is crucial for high recall.
        # Metric is L2 for Euclidean distance as specified by SIFT1M.
        self.index = faiss.IndexHNSWFlat(self.dim, m, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Optionally make faiss verbose
        self.index.verbose = kwargs.get("verbose", False)


    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        For HNSW, this involves building the graph structure. Can be called
        multiple times to add vectors incrementally.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # FAISS requires float32 data.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        self.index.add(xb)
        self.is_trained = True


    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances.
                - indices: shape (nq, k), dtype int64, indices into base vectors.
        """
        if not self.is_trained:
            # Return empty results if index has no data
            nq = xq.shape[0]
            return np.full((nq, k), -1.0, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # FAISS requires float32 queries.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # The efSearch parameter can be dynamically adjusted before searching,
        # but we use the one set at initialization for consistency.
        # self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, k)
        
        # FAISS HNSW returns L2 squared distances. The problem allows L2 or L2-squared.
        # No need to sqrt, as it doesn't change the order of neighbors.
        return distances, indices
