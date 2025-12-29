import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction for HNSW)

        Example:
            index = YourIndexClass(dim=128, M=64, ef_search=400)
        """
        self.dim = dim
        
        self.M = int(kwargs.get('M', 48))
        self.ef_construction = int(kwargs.get('ef_construction', 200))
        self.ef_search = int(kwargs.get('ef_search', 96))

        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32

        Notes:
            - Can be called multiple times (cumulative)
            - Must handle large N (e.g., 1,000,000 vectors)

        Example:
            index.add(xb)  # xb.shape = (1000000, 128)
        """
        if not xb.flags['C_CONTIGUOUS'] or xb.dtype != np.float32:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 distances
                - indices: shape (nq, k), dtype int64, indices into base vectors

        Notes:
            - Must return exactly k neighbors per query
            - Indices should refer to positions in the vectors passed to add()
            - Lower distance = more similar

        Example:
            D, I = index.search(xq, k=1)  # xq.shape = (10000, 128)
            # D.shape = (10000, 1), I.shape = (10000, 1)
        """
        self.index.hnsw.efSearch = self.ef_search
        
        if not xq.flags['C_CONTIGUOUS'] or xq.dtype != np.float32:
            xq = np.ascontiguousarray(xq, dtype=np.float32)

        distances, indices = self.index.search(xq, k)
        
        return distances, indices