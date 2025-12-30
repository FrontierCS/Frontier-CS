import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An optimized Faiss index for the Recall80 Latency Tier.

    This implementation uses Faiss's IndexIVFPQ, which combines an inverted file
    structure (IVF) for partitioning the vector space with Product Quantization (PQ)
    for compressing the vectors. This combination is highly effective for achieving
    the extremely low latency required by this tier while maintaining the necessary
    80% recall.

    Hyperparameters have been chosen based on established benchmarks for the SIFT1M
    dataset to provide a strong starting point:
    - `nlist=4096`: A large number of partitions to keep each cell small, which is
      beneficial when searching only a few cells (`nprobe`).
    - `M=32`: A relatively high number of sub-quantizers for PQ, improving the
      accuracy of distance approximations from compressed codes.
    - `nprobe=8`: A small number of cells to search per query. This is the primary
      lever for controlling the speed-recall trade-off. This value is a safe
      starting point estimated to exceed the 80% recall threshold.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M).
            **kwargs: Optional parameters to override index defaults.
                      Supported keys: 'nlist', 'M', 'nbits', 'nprobe'.
        """
        self.dim = dim
        self.is_trained = False
        self.ntotal = 0

        # Hyperparameters with defaults optimized for the Recall80 Latency tier.
        self.nlist = kwargs.get('nlist', 4096)
        self.M = kwargs.get('M', 32)
        self.nbits = kwargs.get('nbits', 8)
        self.nprobe = kwargs.get('nprobe', 8)

        if self.dim % self.M != 0:
            raise ValueError(
                f"Vector dimension {self.dim} is not divisible by M={self.M}"
            )

        # The coarse quantizer for IVF partitions. IndexFlatL2 is standard.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # Main index using IVFPQ. Metric is L2 for SIFT1M.
        self.index = faiss.IndexIVFPQ(
            quantizer, self.dim, self.nlist, self.M, self.nbits, faiss.METRIC_L2
        )
        
        # Set search-time parameter `nprobe`.
        self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. If the index is not yet trained, it will
        first be trained on a random subset of the provided data.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        if not self.is_trained:
            # Train the index on a subset of the data for efficiency.
            # 100,000 vectors is a robust choice for training on SIFT1M.
            ntrain = min(xb.shape[0], 100_000)
            random_indices = np.random.choice(
                xb.shape[0], size=ntrain, replace=False
            )
            xt = xb[random_indices]
            
            self.index.train(xt)
            self.is_trained = True

        # Add the full set of vectors to the trained index.
        self.index.add(xb)
        self.ntotal = self.index.ntotal

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), L2-squared distances.
                - indices: shape (nq, k), 0-based indices of the nearest neighbors.
        """
        if not self.is_trained:
            raise RuntimeError("Index must be trained via add() before searching.")
        
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        
        if self.ntotal == 0:
            # Handle search on an empty index.
            distances = np.full((xq.shape[0], k), -1.0, dtype=np.float32)
            indices = np.full((xq.shape[0], k), -1, dtype=np.int64)
            return distances, indices

        distances, indices = self.index.search(xq, k)
        return distances, indices