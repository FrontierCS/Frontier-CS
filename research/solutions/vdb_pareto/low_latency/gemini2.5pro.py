import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        This index uses Faiss's IndexIVFPQ, which is a highly efficient algorithm
        for CPU-based similarity search. It's configured with parameters that
        aggressively prioritize low latency to meet the strict time constraints,
        while aiming for the highest possible recall within that budget.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters to override index configuration.
        """
        self.dim = dim
        self.is_trained = False

        # --- Hyperparameters for IVFPQ, tuned for the Low Latency Tier ---
        
        # nlist: Number of inverted lists (Voronoi cells). A higher number allows
        # for a smaller `nprobe`, which is crucial for speed.
        self.nlist = kwargs.get('nlist', 4096)
        
        # m: Number of sub-quantizers for Product Quantization. For d=128, m=16
        # splits vectors into 16 sub-vectors of 8 dimensions each, providing
        # a good trade-off between compression (speed) and accuracy (recall).
        self.m = kwargs.get('m', 16)
        
        # nbits: Bits per sub-quantizer code. 8 is the standard value.
        self.nbits = 8
        
        # The coarse quantizer used to assign vectors to inverted lists.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # The main index object. METRIC_L2 specifies Euclidean distance.
        self.index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)

        # nprobe: The number of inverted lists to search at query time. This is
        # the most critical parameter for the speed-vs-recall trade-off.
        # A low value like 8 is chosen to stay well within the 2.31ms latency cap,
        # based on typical SIFT1M benchmarks.
        self.nprobe = kwargs.get('nprobe', 8)
        self.index.nprobe = self.nprobe

        # The evaluation environment has 8 vCPUs. We configure Faiss to use them
        # for parallelization during search, which is essential for batch performance.
        n_threads = kwargs.get('n_threads', 8)
        faiss.omp_set_num_threads(n_threads)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. If the index has not been trained yet,
        it will be trained on a random sample of the first batch of vectors.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        # Faiss requires C-contiguous float32 arrays for optimal performance.
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
        elif xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        if not self.is_trained:
            # Training is required to learn the centroids for IVF and PQ.
            # We train on a random sample to be efficient and avoid bias.
            # A sample size of ~50 per centroid is a good rule of thumb.
            n_train_samples = self.nlist * 50
            if xb.shape[0] >= n_train_samples:
                random_indices = np.random.choice(xb.shape[0], size=n_train_samples, replace=False)
                train_set = xb[random_indices]
            else:
                train_set = xb
            
            self.index.train(train_set)
            self.is_trained = True

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances.
                - indices: shape (nq, k), dtype int64, indices into base vectors.
        """
        # Ensure query vectors are in the correct format for Faiss.
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
        elif xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        distances, indices = self.index.search(xq, k)
        
        return distances, indices