import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An index optimized for the Recall80 Latency Tier.

    This implementation uses FAISS's IndexIVFPQ, a highly efficient index structure
    for large-scale similarity search on CPUs. It combines two approximation techniques:
    1.  Inverted File (IVF): The vector space is partitioned into `nlist` clusters
        (Voronoi cells). At search time, only a small subset (`nprobe`) of these
        clusters are visited, drastically reducing the search space.
    2.  Product Quantization (PQ): Vectors within each cluster's inverted list are
        compressed. This reduces the memory footprint and accelerates distance
        calculations by using lookup tables instead of full vector operations.

    The hyperparameters are specifically tuned to meet the problem's constraints:
    achieve at least 80% recall@1 while minimizing query latency below 0.6ms.

    - `nlist=1024`: A standard number of clusters for a 1M vector dataset, providing
      a good balance between partitioning granularity and quantizer search speed.
    - `m=16`: The number of subquantizers for PQ. For the 128-dim SIFT vectors, this
      compresses each vector to 16 bytes, enabling very fast distance computations.
    - `nprobe=6`: The number of clusters to visit per query. This is the most
      critical parameter for the speed/recall tradeoff. A value of 6 is chosen
      as an aggressive but calculated setting to push latency as low as possible
      while still being expected to clear the 80% recall gate for the SIFT1M dataset.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M).
            **kwargs: Optional parameters to override tuned defaults.
                      Supported keys: 'nlist', 'm', 'nprobe'.
        """
        self.dim = dim
        self.index = None

        # Tuned hyperparameters for this specific problem
        self.nlist = kwargs.get('nlist', 1024)
        self.m = kwargs.get('m', 16)
        self.nbits = 8  # Standard: 2^8=256 centroids per PQ sub-quantizer
        self.nprobe = kwargs.get('nprobe', 6)

        if self.dim % self.m != 0:
            raise ValueError(f"Dimension {self.dim} must be divisible by m={self.m}")

        # The coarse quantizer (IVF part) maps vectors to clusters.
        # IndexFlatL2 performs an exact search for the nearest cluster centroids.
        quantizer = faiss.IndexFlatL2(self.dim)

        # The main index combines IVF with PQ.
        # METRIC_L2 computes squared Euclidean distances, which is faster and
        # acceptable per the problem statement.
        self.index = faiss.IndexIVFPQ(
            quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2
        )

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        If the index is not yet trained, it will be trained on the provided
        vectors first. Training involves running k-means to find the `nlist`
        cluster centroids and learning the PQ codebooks.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if not self.index.is_trained:
            # faiss.IndexIVFPQ requires a training step.
            self.index.train(xb)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, squared L2 distances.
                - indices: shape (nq, k), dtype int64, indices into base vectors.
        """
        # Set the number of probes for this search. This is the main knob for
        # controlling the speed vs. accuracy tradeoff at query time.
        self.index.nprobe = self.nprobe

        distances, indices = self.index.search(xq, k)

        return distances, indices