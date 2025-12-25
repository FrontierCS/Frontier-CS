import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    """
    An efficient Vector Database index for the Recall80 Latency Tier.

    This implementation uses FAISS's IndexIVFPQ, a highly optimized method
    that combines Inverted Files (for partitioning the search space) and
    Product Quantization (for vector compression and fast distance calculation).

    The hyperparameters (nlist, m, nprobe) are carefully selected based on
    public benchmarks for the SIFT1M dataset to achieve the target recall
    of >= 80% while minimizing query latency.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters for hyperparameter tuning.
        """
        # --- Environment Optimization ---
        # Utilize all available CPU cores for FAISS operations. The evaluation
        # environment provides 8 vCPUs.
        try:
            faiss.omp_set_num_threads(8)
        except AttributeError:
            # This may happen if FAISS is compiled without OpenMP support.
            # The code will still work but might be slower.
            pass

        self.dim = dim
        self.is_trained = False

        # --- Index Hyperparameters ---
        # These values are chosen to balance the recall/latency trade-off for SIFT1M.
        # `nlist`: Number of partitions (Voronoi cells).
        # `m`: Number of sub-vectors for Product Quantization.
        # `nprobe`: Number of partitions to search at query time. This is the
        #           primary knob for controlling the speed vs. accuracy trade-off.
        self.nlist = kwargs.get('nlist', 1024)
        self.m = kwargs.get('m', 16)  # 128 is divisible by 16
        self.nbits = kwargs.get('nbits', 8)  # 8 bits -> 256 centroids per sub-quantizer
        
        # A value of nprobe=5 is chosen as a safe margin to exceed the 80% recall
        # gate, based on SIFT1M benchmarks.
        self.nprobe = kwargs.get('nprobe', 5)

        # --- Index Construction ---
        # 1. Quantizer: A simple index to find the nearest cells for a query vector.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # 2. Main Index: IndexIVFPQ combines the quantizer with inverted lists
        #    and product quantization for memory efficiency and fast search.
        self.index = faiss.IndexIVFPQ(
            quantizer,
            self.dim,
            self.nlist,
            self.m,
            self.nbits,
            faiss.METRIC_L2
        )
        
        # Set the number of probes for the search method.
        self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        
        If the index is not yet trained, it uses a subset of the first data
        batch `xb` to train the quantizer and PQ codebooks.
        """
        # FAISS operates on float32 arrays.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        if not self.is_trained:
            # Training is required before adding vectors.
            # We select a subset of the input data for training.
            # 100,000 vectors is a robust sample size for training on SIFT1M.
            ntrain = min(xb.shape[0], 100_000)
            
            # Randomly sample to avoid any bias from data ordering.
            if xb.shape[0] > ntrain:
                random_indices = np.random.choice(xb.shape[0], size=ntrain, replace=False)
                xt = xb[random_indices]
            else:
                xt = xb
            
            self.index.train(xt)
            self.is_trained = True
        
        # Add the vectors to the inverted lists.
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for the k nearest neighbors for each query vector.

        Returns:
            A tuple of (distances, indices).
            - distances: L2-squared distances, shape (nq, k)
            - indices: 0-based indices of the neighbors, shape (nq, k)
        """
        if not self.is_trained or self.index.ntotal == 0:
            # Handle search on an empty or untrained index.
            nq = xq.shape[0]
            return (
                np.full((nq, k), -1, dtype=np.float32),
                np.full((nq, k), -1, dtype=np.int64)
            )

        # Ensure query vectors are float32.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Perform the search.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
