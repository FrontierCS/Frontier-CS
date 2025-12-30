import os
from typing import Tuple

import faiss
import numpy as np


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality
            **kwargs: Optional parameters:
                - nlist: number of IVF lists (default: 4096)
                - nprobe: number of lists to probe at search time (default: 256)
                - training_samples: number of vectors to use for training (default: 160000)
                - num_threads: number of FAISS threads to use (default: os.cpu_count())
        """
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        if self.nlist <= 0:
            self.nlist = 1

        self.nprobe = int(kwargs.get("nprobe", 256))
        if self.nprobe <= 0:
            self.nprobe = 1
        self.nprobe = min(self.nprobe, self.nlist)

        self.training_samples = int(kwargs.get("training_samples", 160000))
        if self.training_samples <= 0:
            self.training_samples = 160000

        num_threads = kwargs.get("num_threads", None)
        if num_threads is None or num_threads <= 0:
            try:
                num_threads = os.cpu_count() or 1
            except Exception:
                num_threads = 1
        else:
            num_threads = int(num_threads)
            if num_threads <= 0:
                num_threads = 1
        faiss.omp_set_num_threads(num_threads)

        self._index = None

    def _ensure_index(self) -> None:
        if self._index is None:
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            index.nprobe = self.nprobe
            self._index = index

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
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        xb = np.ascontiguousarray(xb)

        self._ensure_index()

        if not self._index.is_trained:
            n_train = min(self.training_samples, xb.shape[0])
            if n_train > 0:
                train_x = xb[:n_train]
                self._index.train(train_x)

        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            distances: shape (nq, k), dtype float32
            indices: shape (nq, k), dtype int64
        """
        if self._index is None or self._index.ntotal == 0:
            raise ValueError("Index is empty; call add() before search().")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        xq = np.ascontiguousarray(xq)

        k = int(k)
        if k <= 0:
            raise ValueError("k must be a positive integer")

        search_k = min(k, self._index.ntotal)
        distances, indices = self._index.search(xq, search_k)

        if search_k < k:
            nq = xq.shape[0]
            D_full = np.full((nq, k), np.inf, dtype=np.float32)
            I_full = np.full((nq, k), -1, dtype=np.int64)
            D_full[:, :search_k] = distances
            I_full[:, :search_k] = indices
            distances, indices = D_full, I_full

        distances = np.ascontiguousarray(distances, dtype=np.float32)
        indices = np.ascontiguousarray(indices, dtype=np.int64)

        return distances, indices