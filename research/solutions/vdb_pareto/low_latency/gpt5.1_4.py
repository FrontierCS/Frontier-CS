import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Optional kwargs:
            - nlist (int): number of IVF clusters (default: 4096)
            - nprobe (int): number of IVF clusters to search (default: 256)
            - train_size (int): number of training vectors for IVF (default: 100000)
        """
        self.dim = dim
        self.index = None

        # IVF parameters tuned for SIFT1M and low latency
        self.nlist = int(kwargs.get("nlist", 4096))
        if self.nlist <= 0:
            self.nlist = 4096

        self.nprobe = int(kwargs.get("nprobe", 256))
        if self.nprobe <= 0:
            self.nprobe = 256

        self.train_size = int(kwargs.get("train_size", 100000))
        if self.train_size <= 0:
            self.train_size = 100000

    def _build_ivf_index(self, xb: np.ndarray) -> None:
        n, d = xb.shape
        if d != self.dim:
            raise ValueError(f"Dim mismatch: index dim={self.dim}, xb dim={d}")

        # For very small datasets, fall back to exact search
        if n < self.nlist:
            flat_index = faiss.IndexFlatL2(self.dim)
            flat_index.add(xb)
            self.index = flat_index
            return

        quantizer = faiss.IndexFlatL2(self.dim)
        ivf_index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        # Training
        ntrain = min(self.train_size, n)
        # Ensure at least nlist training points when possible
        if ntrain < self.nlist and n >= self.nlist:
            ntrain = self.nlist

        if n > ntrain:
            # Random subset for training
            rng = np.random.default_rng(1234)
            train_indices = rng.choice(n, size=ntrain, replace=False)
            train_x = xb[train_indices]
        else:
            train_x = xb

        ivf_index.train(train_x)
        ivf_index.nprobe = self.nprobe
        ivf_index.add(xb)

        self.index = ivf_index

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Input xb must have shape (N, {self.dim}), got {xb.shape}")

        xb = np.ascontiguousarray(xb)

        if self.index is None:
            # Build IVF or Flat index on first add
            self._build_ivf_index(xb)
        else:
            # Index already exists, just add
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32
                - indices: shape (nq, k), dtype int64
        """
        if self.index is None or self.index.ntotal == 0:
            xq = np.asarray(xq)
            nq = xq.shape[0]
            D = np.full((nq, k), np.float32(np.inf), dtype=np.float32)
            I = -np.ones((nq, k), dtype=np.int64)
            return D, I

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Input xq must have shape (nq, {self.dim}), got {xq.shape}")

        xq = np.ascontiguousarray(xq)

        # Ensure IVF index uses configured nprobe
        if isinstance(self.index, faiss.IndexIVF):
            self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32)
        if I.dtype != np.int64:
            I = I.astype(np.int64)
        return D, I