import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An efficient Vector Database index for the Low Latency Tier problem.

    This implementation uses FAISS's IndexIVFPQ, a highly optimized method for
    Approximate Nearest Neighbor (ANN) search. It's designed for a balance of
    speed, memory usage, and recall, making it suitable for large datasets under
    strict latency constraints.

    The strategy is to partition the vector space into a large number of cells
    (`nlist`) and then, at query time, only search a small subset of these cells
    (`nprobe`). This drastically reduces the number of vectors that need to be
    compared. Product Quantization (PQ) is used to compress the vectors,
    which reduces memory footprint and accelerates distance calculations within
    the selected cells.

    Key parameter choices for this low-latency scenario:
    - nlist=4096: A relatively large number of cells to create a fine-grained
      partition of the 1M vector dataset.
    - m=32: The number of sub-quantizers for PQ. 128 (dim) / 32 = 4D
      sub-vectors, providing good compression and fast lookups.
    - nprobe=5: A very small number of cells to search. This is the most
      critical parameter for meeting the aggressive latency target of < 2.31ms.
      It prunes the search space by ~99.9%.

    Multi-threading is enabled to leverage the 8 vCPUs available in the
    evaluation environment, speeding up both index construction and search.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for index tuning.
                - nlist: Number of Voronoi cells for the IVF index.
                - m: Number of sub-quantizers for PQ.
                - nprobe: Number of cells to search at query time.
        """
        self.dim = dim
        self.is_trained = False

        # Parameters for IndexIVFPQ, tuned for the low latency tier.
        self.nlist = kwargs.get('nlist', 4096)
        self.m = kwargs.get('m', 32)
        self.nbits = 8  # 8 bits per sub-quantizer, standard for PQ.
        self.metric = faiss.METRIC_L2

        # The crucial search-time parameter for the speed-recall trade-off.
        self.nprobe = kwargs.get('nprobe', 5)

        # Set FAISS to use all available CPU cores (8 in the eval env)
        # This significantly speeds up training and batch search.
        try:
            faiss.omp_set_num_threads(8)
        except AttributeError:
            # This might happen if FAISS is compiled without OpenMP support.
            # The evaluation environment should have it.
            pass

        # 1. Coarse quantizer: maps a vector to a cell. IndexFlatL2 is a brute-force L2 index.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # 2. Main index: uses the quantizer to partition data.
        self.index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)


    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. If the index is not trained, it will be
        trained on the first batch of vectors provided.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # Training the index involves finding the 'nlist' cluster centroids.
            # This only needs to be done once. The evaluation script calls add()
            # with the full 1M vectors, which is sufficient for training.
            print(f"Training IVF-PQ index on {xb.shape[0]} vectors...")
            self.index.train(xb)
            self.is_trained = True
            print("Training complete.")
        
        # Add the vectors to the inverted lists.
        self.index.add(xb)
        print(f"Added {xb.shape[0]} vectors. Total vectors in index: {self.index.ntotal}")

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
        # Set the number of cells to probe. This is the most critical parameter
        # for controlling the latency-recall trade-off.
        self.index.nprobe = self.nprobe
        
        # FAISS search is batched and parallelized, efficiently handling all queries.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices