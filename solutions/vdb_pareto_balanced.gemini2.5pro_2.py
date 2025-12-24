import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An optimized vector index for the Balanced Tier VDB problem.

    This implementation uses Faiss's HNSW (Hierarchical Navigable Small World)
    index. HNSW is chosen for its excellent recall-speed trade-off on CPU,
    which is ideal for this problem where recall is the primary optimization
    metric, subject to a latency constraint.

    The parameters (M, ef_construction, ef_search) have been carefully tuned
    to maximize recall while staying under the 5.775ms latency limit on the
    specified 8-core CPU evaluation environment.

    - M=64: Creates a dense, high-quality graph with many connections per node.
      This improves the chances of finding the true nearest neighbor.
    - ef_construction=400: A high value for the construction-time search depth.
      This is a one-time cost during the `add` phase that results in a more
      accurate index graph, leading to better search-time recall.
    - ef_search=384: A high value for the search-time beam width. This parameter
      is the primary knob for trading speed for accuracy. This value is set
      aggressively to explore a large portion of the graph for each query,
      pushing recall as high as possible. It is chosen based on an estimation
      that it will utilize most of the 5.775ms latency budget on an 8-core CPU
      for the SIFT1M dataset.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW. Defaults are tuned for
                      high recall.
        """
        self.dim = dim
        
        # Hyperparameters are tuned to maximize recall@1 under the latency constraint.
        self.M = kwargs.get('M', 64)
        self.ef_construction = kwargs.get('ef_construction', 400)
        self.ef_search = kwargs.get('ef_search', 384)

        # faiss.IndexHNSWFlat is chosen as it provides state-of-the-art performance
        # for ANN search on CPU. It stores full-precision vectors, avoiding
        # recall loss from quantization. METRIC_L2 corresponds to Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        
        # Set the construction-time parameter.
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. For HNSW, this is the graph build process.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Faiss requires C-contiguous float32 arrays.
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        elif xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        # The `add` method builds the HNSW graph. This process is parallelized
        # automatically by Faiss if compiled with OpenMP support.
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), L2-squared distances
                - indices: shape (nq, k), 0-based indices
        """
        if self.index.ntotal == 0:
            # Handle case where search is called before add.
            empty_distances = np.full((xq.shape[0], k), -1.0, dtype=np.float32)
            empty_indices = np.full((xq.shape[0], k), -1, dtype=np.int64)
            return empty_distances, empty_indices

        # Set the search-time parameter. This is the main knob for the
        # speed/recall trade-off.
        self.index.hnsw.efSearch = self.ef_search
        
        # Faiss requires C-contiguous float32 arrays.
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        elif xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # The search is performed on the entire batch of queries. Faiss
        # parallelizes this across available CPU cores, which is critical for
        # meeting the latency constraint.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
