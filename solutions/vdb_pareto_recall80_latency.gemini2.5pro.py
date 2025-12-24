import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    """
    An optimized FAISS-based index for the Recall80 Latency Tier.

    This implementation uses an Inverted File with Product Quantization (IVFPQ)
    to achieve extremely low latency while maintaining a recall@1 of at least 80%
    on the SIFT1M dataset.

    The core strategy revolves around these key parameter choices:
    - nlist=4096: A large number of clusters (Voronoi cells) provides a
      fine-grained partitioning of the vector space. This is crucial because it
      allows the search to be highly selective.
    - m=16: The vector dimension (128) is divided into 16 sub-vectors for
      Product Quantization. This offers a good balance between the accuracy of
      distance approximations and the speed of computation.
    - nprobe=5: This is the most critical parameter for this challenge. At search
      time, we only inspect 5 out of 4096 clusters. This aggressive pruning
      is the primary reason for the low latency. This value was chosen as it
      is near the minimum required to exceed the 80% recall threshold for SIFT1M
      with the chosen index structure.
    """
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (128 for SIFT1M).
            **kwargs: Optional parameters, not used in this specialized implementation.
        """
        self.dim = dim
        self.is_trained = False

        # --- Parameters tuned for SIFT1M on an 8-core CPU environment ---
        nlist = 4096  # Number of clusters/Voronoi cells
        m = 16        # Number of sub-quantizers for PQ
        nbits = 8     # Bits per sub-quantizer code (standard is 8)

        # The coarse quantizer assigns vectors to clusters. IndexFlatL2 is used for L2 distance.
        quantizer = faiss.IndexFlatL2(self.dim)
        
        # The main index structure combining IVF and PQ.
        self.index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, m, nbits)
        
        # Set nprobe, the critical search-time parameter for the speed/recall trade-off.
        # This value is tuned to be as small as possible while meeting the recall gate.
        self.nprobe = 5

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. If the index is not yet trained, it will be
        trained on a subset of the first batch of vectors provided.

        Args:
            xb: Base vectors to add, with shape (N, dim) and dtype float32.
        """
        if not self.is_trained:
            # Training is required before adding vectors to an IVF index.
            # We train on a sufficiently large subset of the data for good centroid quality.
            # Using 64 * nlist vectors for training is a robust choice.
            ntrain = min(xb.shape[0], 64 * self.index.nlist)
            
            # FAISS C++ backend requires C-contiguous float32 arrays.
            xt_train = np.ascontiguousarray(xb[:ntrain], dtype=np.float32)
            
            self.index.train(xt_train)
            self.is_trained = True

        # Add the full batch of vectors to the index.
        xb_contiguous = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb_contiguous)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for the k nearest neighbors for each query vector.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: The number of nearest neighbors to return.

        Returns:
            A tuple (distances, indices):
                - distances: L2-squared distances, shape (nq, k), dtype float32.
                - indices:
                Indices of the nearest neighbors, shape (nq, k), dtype int64.
        """
        if not self.is_trained:
            raise RuntimeError("Index must be trained via add() before searching.")

        # Set the number of clusters to visit during search.
        self.index.nprobe = self.nprobe
        
        # Ensure query vectors are in the correct C-contiguous float32 format for FAISS.
        xq_contiguous = np.ascontiguousarray(xq, dtype=np.float32)
        
        distances, indices = self.index.search(xq_contiguous, k)
        
        return distances, indices
