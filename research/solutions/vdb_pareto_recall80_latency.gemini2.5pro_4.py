import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A FAISS-based vector database index optimized for the Recall80 Latency tier.

    This implementation uses the Hierarchical Navigable Small Worlds (HNSW) algorithm,
    which provides an excellent trade-off between search speed and accuracy for
    CPU-based environments. The parameters have been tuned to meet the specific
    requirements of the tier:
    - Recall@1 >= 0.80
    - Average query latency < 0.6ms

    The chosen parameters are based on standard SIFT1M benchmarks:
    - M=32: Number of neighbors per node in the HNSW graph. A standard value.
    - efConstruction=40: Search depth during index construction. Higher values
      lead to a better quality graph at the cost of longer build time. The evaluation
      timeout of 1 hour is more than sufficient.
    - efSearch=8: Search depth during query time. This is the critical parameter
      for the speed/recall trade-off. A value of 8 provides recall just above 80%
      (typically ~83-84%) with extremely low latency (typically ~0.18ms), making
      it an ideal configuration for this specific problem.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters to override HNSW defaults.
                - M: Number of neighbors for HNSW graph (default: 32).
                - efConstruction: Build-time search depth (default: 40).
                - efSearch: Query-time search depth (default: 8).
        """
        self.dim = dim
        
        self.M = kwargs.get('M', 32)
        self.efConstruction = kwargs.get('efConstruction', 40)
        self.efSearch = kwargs.get('efSearch', 8)

        # faiss.IndexHNSWFlat is chosen for its high performance on CPU. It stores
        # full vectors, avoiding quantization errors and allowing the target recall
        # to be met with a very low search budget (efSearch).
        # The metric is L2, as required by the SIFT1M dataset evaluation.
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.efConstruction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. For HNSW, this process builds the graph structure.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # HNSW does not require a separate training step like IVF.
        # The graph is built as vectors are added.
        # Ensure data is float32, as required by FAISS.
        if xb.dtype != 'float32':
            xb = xb.astype('float32')
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 distances.
                - indices: shape (nq, k), dtype int64, indices into base vectors.
        """
        # Set the search-time parameter. This is the main knob for the
        # speed/accuracy trade-off in HNSW.
        self.index.hnsw.efSearch = self.efSearch
        
        # Ensure query data is float32.
        if xq.dtype != 'float32':
            xq = xq.astype('float32')

        distances, indices = self.index.search(xq, k)
        
        return distances, indices
