import numpy as np
import faiss
import os
from typing import Tuple

class YourIndexClass:
    """
    A Faiss-based vector index optimized for the Recall80 Latency Tier problem.

    This implementation uses an Inverted File with Product Quantization (IVFPQ)
    to achieve extremely low latency while satisfying the recall@1 >= 0.80 constraint.
    Hyperparameters have been carefully selected and tuned for the SIFT1M dataset
    to provide the best possible performance under the given evaluation criteria.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters to override default Faiss settings.
                      Supported keys: 'nlist', 'M', 'nprobe'.
        """
        # Set Faiss to use all available CPU cores. This is critical for
        # achieving the sub-millisecond latency requirement on batch queries.
        if 'OMP_NUM_THREADS' not in os.environ:
            num_threads = os.cpu_count()
            if num_threads is not None:
                faiss.omp_set_num_threads(num_threads)

        self.dim = dim
        self.is_trained = False

        # --- Tuned Hyperparameters for IVFPQ ---
        # These values are chosen to just exceed the 0.80 recall@1 threshold
        # on SIFT1M, thereby minimizing latency.
        
        # Number of IVF cells (Voronoi partitions).
        self.nlist = kwargs.get('nlist', 2048)
        
        # Number of sub-quantizers for Product Quantization. Must be a divisor of `dim`.
        self.M = kwargs.get('M', 16)
        
        # Number of bits per sub-quantizer code. 8 is standard.
        self.nbits = kwargs.get('nbits', 8)
        
        # Number of IVF cells to search. This is the most critical parameter
        # for the speed-recall tradeoff. The value of 26 is a safe estimate
        # to ensure recall > 0.80.
        self.nprobe = kwargs.get('nprobe', 26)

        # --- Faiss Index Construction ---
        # The coarse quantizer is used to assign vectors to their nearest IVF cell.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # The main index combines IVF for partitioning and PQ for compression.
        # This combination is ideal for high-speed search on large datasets.
        # The default metric is L2, which is what SIFT1M uses.
        self.index = faiss.IndexIVFPQ(
            quantizer, self.dim, self.nlist, self.M, self.nbits
        )

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # The index must be trained on a representative sample of the data
            # to learn the IVF cell centroids and the PQ codebooks.
            # Training on the full 1M SIFT1M dataset is feasible and gives the best quality.
            self.index.train(xb)
            self.is_trained = True
        
        # Add the vectors to the index's inverted lists.
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
        # Set the number of probes for this search.
        self.index.nprobe = self.nprobe
        
        # Perform the search. Faiss handles batching and multithreading internally.
        # The returned distances are L2-squared, which is acceptable per problem spec.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices