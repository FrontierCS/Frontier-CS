import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    A FAISS-based vector index optimized for the low-latency tier.

    This implementation uses an Inverted File with Product Quantization (IVFPQ)
    to achieve very fast search speeds, which is essential to meet the strict
    latency constraint of 2.31ms. The hyperparameters are aggressively tuned
    for speed over recall.

    Index structure:
    - IVF (Inverted File): Partitions the vector space into `nlist` cells.
      At search time, only a small subset of these cells (`nprobe`) are visited.
    - PQ (Product Quantization): Compresses vectors stored in the index. This
      reduces the memory footprint and dramatically speeds up distance
      calculations, as they are computed from compact codes and lookup tables.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters (not used in this implementation,
                      but included for API compatibility).
        """
        self.dim = dim
        self.is_trained = False

        # --- Hyperparameter Tuning for Low Latency ---
        # These parameters are critical for balancing search speed and recall.
        # They have been selected to prioritize meeting the stringent latency
        # target of the low-latency tier.

        # nlist: Number of IVF cells (Voronoi partitions). A moderate number
        # is chosen to balance the cost of the coarse quantization search
        # and the number of vectors scanned per cell.
        nlist = 1024

        # m: Number of subquantizers for Product Quantization.
        # The 128-dimensional vector is split into `m` sub-vectors, and each
        # is quantized separately. A higher `m` results in shorter sub-vectors,
        # leading to faster (but less accurate) distance approximations.
        # `m=32` is chosen for maximum speed (128 / 32 = 4-dim sub-vectors).
        m = 32

        # nbits: Number of bits per subquantizer code. 8 is the standard,
        # yielding 2^8 = 256 centroids for each sub-space.
        nbits = 8

        # --- Index Construction ---
        # The coarse quantizer for IVF. This index is used to assign vectors
        # to their respective Voronoi cells.
        quantizer = faiss.IndexFlatL2(self.dim)

        # The main index combines IVF and PQ.
        # faiss.METRIC_L2 is the default and is used for SIFT1M.
        self.index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, m, nbits)

        # nprobe: The number of IVF cells to probe at search time. This is the
        # most important search-time parameter for the speed/recall trade-off.
        # A very low value is required to meet the latency goal, as hinted by
        # the problem description ("nprobe=2-5"). We choose 5 to maximize
        # recall within this aggressive range.
        self.nprobe = 5

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        If the index has not been trained yet, it will be trained on the
        first batch of vectors provided.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if not self.is_trained:
            # The IVFPQ index requires a training step to learn the Voronoi
            # cells (for IVF) and the codebooks (for PQ). We train on the
            # provided base vectors.
            if xb.shape[0] > 0:
                self.index.train(xb)
                self.is_trained = True

        # After training, add the vectors to the index.
        if xb.shape[0] > 0:
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            (distances, indices):
                - distances: shape (nq, k), L2-squared distances.
                - indices: shape (nq, k), indices of the neighbors.
        """
        if xq.shape[0] == 0:
            return np.array([[]], dtype='float32'), np.array([[]], dtype='int64')

        # Set the number of probes for this specific search query. This allows
        # dynamic adjustment, but here we use the fixed value optimized for this tier.
        self.index.nprobe = self.nprobe

        # FAISS's search method is highly optimized for batch processing,
        # which is crucial for meeting the average query time constraint.
        distances, indices = self.index.search(xq, k)

        return distances, indices
