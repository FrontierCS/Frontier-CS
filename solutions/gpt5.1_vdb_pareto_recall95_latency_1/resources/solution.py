import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        IVF-Flat index optimized for high recall (>=0.95) and low latency on SIFT1M.
        """
        self.dim = dim

        # Hyperparameters with reasonable defaults for SIFT1M
        self.nlist = int(kwargs.get("nlist", 4096))   # number of coarse clusters
        self.nprobe = int(kwargs.get("nprobe", 128))  # number of clusters to probe at query time

        # Configure FAISS threading
        try:
            default_threads = faiss.omp_get_max_threads()
        except AttributeError:
            default_threads = 1
        self.num_threads = int(kwargs.get("num_threads", default_threads if default_threads > 0 else 1))
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except AttributeError:
            pass  # older FAISS versions may not have this; ignore

        # Build IVF-Flat index (L2 distance)
        quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(quantizer, dim, self.nlist, faiss.METRIC_L2)

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Trains IVF quantizer on first call.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        # Train on a subset of the first batch if not trained yet
        if not self.index.is_trained:
            n_train = min(100000, xb.shape[0])
            if n_train < self.nlist:
                n_train = xb.shape[0]
            train_data = xb[:n_train]
            self.index.train(train_data)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors using IVF-Flat with nprobe clusters.
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        # Ensure index has data
        if self.index.ntotal == 0:
            nq = xq.shape[0]
            distances = np.full((nq, k), np.inf, dtype=np.float32)
            indices = np.full((nq, k), -1, dtype=np.int64)
            return distances, indices

        # Set nprobe for search
        self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
