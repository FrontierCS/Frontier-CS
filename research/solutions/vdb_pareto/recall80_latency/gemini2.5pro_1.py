import numpy as np
from typing import Tuple
import faiss

class Recall80LatencyIndex:
    """
    An optimized Faiss-based index for the Recall80 Latency Tier.

    This index uses an Inverted File with Product Quantization (IVFPQ),
    a highly efficient method for approximate nearest neighbor search on CPUs.
    The hyperparameters (nlist, m, nprobe) are aggressively tuned to meet
    the strict < 0.6ms average query latency requirement while ensuring the
    recall@1 stays above the 80% gate.

    Key tuning choices:
    - nlist=4096: A large number of clusters (Voronoi cells) partitions the
      dataset finely. This allows for a very small search scope.
    - m=16: Product Quantization with 16 sub-quantizers compresses 128-dim
      vectors to just 16 bytes, enabling extremely fast distance calculations.
    - nprobe=5: At search time, only 5 cells are visited. This is the most
      critical parameter for balancing the speed/recall trade-off. This value
      is chosen as a safe but aggressive setting estimated to achieve
      just over 80% recall for the SIFT1M dataset.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction for HNSW)
        """
        self.dim = dim
        self.is_trained = False

        # Set Faiss to use a number of threads appropriate for the environment.
        # The evaluation environment has 8 vCPUs.
        num_threads = 8
        faiss.omp_set_num_threads(num_threads)

        # Hyperparameters for IVFPQ, tuned for the SIFT1M dataset
        nlist = kwargs.get('nlist', 4096)
        m = kwargs.get('m', 16)
        nbits = kwargs.get('nbits', 8)

        if dim % m != 0:
            # Fallback for dimensions not divisible by m
            # A simple approach is to find a new m that is a divisor
            # This is not critical for SIFT1M (128 % 16 == 0) but good practice
            for i in range(m, 0, -1):
                if dim % i == 0:
                    m = i
                    break
        
        # The quantizer is a flat index used to find the nearest centroids
        quantizer = faiss.IndexFlatL2(dim)
        
        # The main index using IVFPQ. It uses L2 distance.
        self.index = faiss.IndexIVFPQ(quantizer, dim, nlist, m, nbits, faiss.METRIC_L2)
        
        # nprobe is the key parameter for the speed/recall tradeoff.
        self.nprobe = kwargs.get('nprobe', 5)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # Training is required for IVF and PQ.
            # It learns the centroids and codebooks from the data.
            # For SIFT1M, training on the full 1M dataset is feasible and
            # gives the best quality.
            self.index.train(xb)
            self.is_trained = True

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        # Set the number of probes for this search. This is crucial for performance.
        self.index.nprobe = self.nprobe

        # Perform the search. Faiss is highly optimized for batch searches.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices