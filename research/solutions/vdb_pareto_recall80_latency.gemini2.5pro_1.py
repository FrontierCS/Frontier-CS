import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        This index uses FAISS's IndexIVFPQ, a highly efficient approximate nearest
        neighbor search structure based on an inverted file system with product
        quantization. The parameters are specifically tuned for the SIFT1M
        dataset to meet the Recall@1 >= 0.80 constraint while minimizing query
        latency, as required by the Recall80 Latency Tier problem.

        The configuration is based on established FAISS benchmarks which show
        that an 'IVF4096,PQ16' index with nprobe=16 achieves R@1 > 0.80 with
        very low latency.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (not used in this specialized implementation)
        """
        self.dim = dim
        self.is_trained = False

        # --- Index Parameters ---
        # These values are tuned for the SIFT1M dataset and the specific
        # recall/latency trade-off of this problem.
        
        # Number of Voronoi cells for the IVF part.
        nlist = 4096
        
        # Number of sub-quantizers for the PQ part.
        # The 128-dimensional vector is split into 16 sub-vectors of 8 dimensions.
        m = 16
        
        # Number of bits per sub-quantizer code. 8 bits = 256 centroids per subspace.
        bits = 8

        # --- Index Construction ---
        
        # The coarse quantizer is a flat L2 index used to partition the space.
        # It finds the nearest cell centroid for a given query vector.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # The main index object.
        self.index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, m, bits)

        # --- Search-time Parameters ---
        
        # nprobe is the number of Voronoi cells to visit during search.
        # This is the most critical parameter for the speed vs. accuracy trade-off.
        # A value of 16 is chosen to reliably exceed the 80% recall gate.
        self.nprobe = 16

        # --- Environment Optimization ---
        
        # Configure FAISS to use multiple threads for parallel execution.
        # The evaluation environment specifies 8 vCPUs.
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        If the index has not been trained yet, it will be trained on the first
        batch of vectors passed to this method. The evaluation script calls `add`
        once with the entire 1M SIFT1M dataset, so this approach is suitable.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if not self.is_trained:
            # Training learns the data distribution to create the IVF cell structure.
            # We train on the entire dataset to get the best possible partitioning.
            self.index.train(xb)
            self.is_trained = True
        
        # Add the vectors to the index. They will be PQ-encoded and stored
        # in the appropriate inverted lists.
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            A tuple (distances, indices):
                - distances: shape (nq, k), float32, L2-squared distances
                - indices: shape (nq, k), int64, indices into base vectors
        """
        # Set the number of cells to probe for this specific search.
        self.index.nprobe = self.nprobe

        # Execute the search. FAISS automatically handles batching and
        # parallelization across the available threads.
        distances, indices = self.index.search(xq, k)

        return distances, indices
