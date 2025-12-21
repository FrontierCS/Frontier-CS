import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An index for the low-latency tier, optimized for recall under a strict
    latency constraint. It uses Faiss's HNSW (Hierarchical Navigable Small World)
    implementation, which provides an excellent speed-recall trade-off.

    The strategy is to use HNSW with full-precision vectors (IndexHNSWFlat)
    to avoid recall loss from quantization, and tune the `efSearch` parameter
    aggressively to meet the strict latency target. Based on the problem's
    hints ("aggressive approximation", "HNSW efSearch=50-100") and typical
    HNSW performance, we choose parameters that favor speed.

    - M=16: A standard value for HNSW graph connectivity, balancing memory/build
      time and search performance. It aligns with the example in the prompt.
    - ef_construction=200: A reasonably high value to ensure a good quality
      graph is built, as build time is not the primary constraint.
    - ef_search=80: The most critical parameter. It's set within the hinted
      range (50-100) to be fast enough for the 2.31ms latency target while
      retaining as much recall as possible.
    
    The implementation leverages Faiss's automatic parallelization over the
    query batch by setting the number of OpenMP threads to match the
    evaluation environment's 8 vCPUs.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW (M, ef_construction, ef_search)
        """
        self.dim = dim
        
        self.M = kwargs.get('M', 16)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 80)
        
        # The evaluation environment has 8 vCPUs. We utilize them for parallel search.
        faiss.omp_set_num_threads(8)

        # Initialize the HNSW index. METRIC_L2 is used for Euclidean distance.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. For HNSW, this builds the graph.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # Faiss requires float32 data type.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices): Tuple of distances and indices.
        """
        # Faiss requires float32 data type.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        # efSearch is the key search-time parameter for HNSW, balancing speed and recall.
        self.index.hnsw.efSearch = self.ef_search
        
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
