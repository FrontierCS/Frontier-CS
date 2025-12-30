import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for the FAISS IVFPQ index.
                      - nlist (int): Number of IVF cells. Default: 1024.
                      - m (int): Number of PQ sub-quantizers. Default: 16.
                      - nbits (int): Bits per PQ code. Default: 8.
                      - nprobe (int): Number of IVF cells to probe at search time. Default: 4.
                      - num_threads (int): Number of threads for FAISS. Default: 8.
        """
        self.dim = dim
        self.is_trained = False

        # Parameters are tuned for the low-latency tier, prioritizing speed.
        self.nlist = kwargs.get("nlist", 1024)
        self.m = kwargs.get("m", 16)
        self.nbits = kwargs.get("nbits", 8)
        self.nprobe = kwargs.get("nprobe", 4)
        num_threads = kwargs.get("num_threads", 8)

        # Set FAISS to use multiple threads for parallel computation.
        faiss.omp_set_num_threads(num_threads)
        
        if self.dim % self.m != 0:
            raise ValueError(f"Vector dimension {self.dim} must be divisible by m={self.m}")

        # The coarse quantizer for IVF partitions the vector space.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # The main index combines Inverted File (IVF) for partitioning
        # and Product Quantization (PQ) for vector compression. This combination
        # is memory-efficient and very fast for search.
        self.index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)
        
        # nprobe is the most critical parameter for the speed/recall trade-off.
        # A small value is chosen to meet the strict latency constraint.
        self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # Train the index on a subset of the data to learn the IVF centroids
            # and PQ codebooks. A training set size of 30x to 100x nlist is typical.
            num_train_vectors = min(xb.shape[0], self.nlist * 100)
            
            # FAISS expects C-contiguous arrays for performance.
            train_vectors = np.ascontiguousarray(xb[:num_train_vectors])
            
            self.index.train(train_vectors)
            self.is_trained = True

        # Add the full dataset to the trained index.
        self.index.add(np.ascontiguousarray(xb))

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
        # FAISS search requires C-contiguous arrays for optimal performance.
        xq_contiguous = np.ascontiguousarray(xq)
        
        distances, indices = self.index.search(xq_contiguous, k)
        
        # The problem allows for L2 or L2-squared distances.
        # FAISS IVFPQ returns L2-squared, which is faster as it avoids sqrt.
        return distances, indices