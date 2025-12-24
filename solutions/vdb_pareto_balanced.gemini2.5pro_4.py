import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    """
    An optimized vector database index using Faiss's HNSW implementation.

    This index is specifically tuned to maximize recall@1 for the SIFT1M dataset
    under the specified latency constraint (5.775ms). The strategy relies on
    creating a high-quality HNSW graph and performing an extensive search to
    achieve high recall, leveraging the batch query evaluation on a multi-core
    CPU environment.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (not used in this optimized implementation)
        """
        self.dim = dim

        # --- Parameter Selection for HNSW ---
        # The strategy is to use a high-quality HNSW (Hierarchical Navigable
        # Small World) index to maximize recall, while tuning `efSearch` to
        # stay within the latency budget of 5.775ms. The evaluation is on a
        # multi-core CPU with batch queries, allowing for aggressive (high)
        # parameter settings that prioritize recall over absolute speed.

        # M: Number of neighbors per node in the graph. A larger M creates a
        # denser, higher-quality graph, which improves recall. M=48 is a
        # robust choice for high-recall scenarios on datasets like SIFT1M.
        M = 48

        # efConstruction: A build-time parameter controlling graph quality.
        # Higher values lead to better graphs but longer build times. The
        # 1-hour total time limit is ample, so a high value of 400 is chosen
        # to ensure a high-quality index structure.
        ef_construction = 400

        # efSearch: The critical search-time parameter. It determines how many
        # entry points are explored in the graph during a search. A higher
        # value increases recall at the cost of latency. Given the 5.775ms
        # budget and parallel batch execution on 8 vCPUs, a high value of
        # 512 is chosen to push recall as high as possible, aiming to exceed
        # the baseline recall of 0.9914.
        self.ef_search = 512

        # Initialize the FAISS HNSW index. We use IndexHNSWFlat because it
        # avoids the quantization error of PQ-based methods, which is critical
        # for maximizing recall. The SIFT1M dataset uses the L2 (Euclidean) metric.
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        # Set verbosity to false to keep logs clean during evaluation.
        self.index.verbose = False


    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. For HNSW, this process builds the graph.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # Faiss requires input arrays to be of dtype float32.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        # Faiss's HNSW `add` method is parallelized if compiled with OpenMP,
        # which is standard for the `faiss-cpu` package. This speeds up the
        # index construction phase significantly on multi-core machines.
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
        # Ensure query vectors are of dtype float32.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time exploration factor to our tuned value. This is
        # the primary lever for controlling the speed/recall trade-off.
        self.index.hnsw.efSearch = self.ef_search

        # The `search` method in Faiss is highly optimized for batch queries
        # and will automatically leverage multiple CPU cores (via OpenMP)
        # to process the batch in parallel. This is essential for meeting the
        # strict latency constraint while using a high efSearch value.
        distances, indices = self.index.search(xq, k)

        return distances, indices
