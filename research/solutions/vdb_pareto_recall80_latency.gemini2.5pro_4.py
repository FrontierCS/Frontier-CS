import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An optimized FAISS-based index for the Recall80 Latency Tier problem.

    This index uses an Inverted File with Product Quantization (IVFPQ) structure,
    which is highly effective for large-scale similarity search on CPUs. The
    parameters are specifically tuned to meet the aggressive latency target
    (< 0.6ms average query time) while satisfying the recall constraint (>= 80% @1).

    Key parameter choices:
    - nlist=4096: A large number of centroids to create fine-grained partitions
      of the vector space. This improves the chance that a query's true nearest
      neighbor is in one of the first few lists checked.
    - m=32: A high number of sub-quantizers for Product Quantization. For a 128-dim
      vector, this breaks it into 32 sub-vectors of 4 dimensions each. This
      provides a more accurate distance approximation compared to smaller 'm' values,
      which is crucial for maintaining recall.
    - nprobe=3: An extremely small number of inverted lists to probe at search
      time. This is the primary lever for minimizing latency. By searching only 3
      out of 4096 lists, we drastically reduce the number of vectors to compare
      against, ensuring ultra-low query times. The combination of high nlist and high
      m is designed to make these 3 lists as effective as possible.
    """

    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            **kwargs: Optional parameters to override the defaults.
                      Supported keys: 'nlist', 'm', 'nprobe'.
        """
        self.dim = dim
        
        self.nlist = kwargs.get('nlist', 4096)
        m = kwargs.get('m', 32)
        
        # Using faiss.index_factory for concise index creation.
        # "IVF{nlist},PQ{m}" creates an IndexIVFPQ with L2 distance by default.
        factory_string = f"IVF{self.nlist},PQ{m}"
        self.index = faiss.index_factory(self.dim, factory_string, faiss.METRIC_L2)
        
        # nprobe is the most critical search-time parameter for the speed/accuracy trade-off.
        # A low value is chosen to meet the strict latency requirement.
        self.nprobe = kwargs.get('nprobe', 3)


    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. This involves training the index on a
        data sample if it hasn't been trained yet, then adding all vectors.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if not self.index.is_trained:
            # Training is required for IVF-based indexes to learn the centroids.
            # We train on a random subset of the data for efficiency and to
            # avoid any ordering bias. FAISS recommends using at least 39*nlist
            # to 256*nlist vectors. 256k is a safe and robust choice.
            n_train_vectors = min(xb.shape[0], 256 * 1024)
            
            random_indices = np.random.permutation(xb.shape[0])[:n_train_vectors]
            train_vectors = xb[random_indices]

            # The train method computes k-means centroids for IVF and learns PQ codebooks.
            self.index.train(train_vectors)

        # After training, add the entire database to the index.
        self.index.add(xb)


    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: L2 distances, shape (nq, k), dtype float32.
                - indices: Vector indices, shape (nq, k), dtype int64.
        """
        # To access IVF-specific attributes like `nprobe`, we must downcast
        # the generic `faiss.Index` object returned by the factory.
        ivf_index = faiss.downcast_index(self.index)
        ivf_index.nprobe = self.nprobe
        
        # Perform the search. FAISS automatically parallelizes the search over
        # the batch of queries using OpenMP, which is critical for performance
        # on a multi-core CPU.
        distances, indices = self.index.search(xq, k)
        
        return distances, indices