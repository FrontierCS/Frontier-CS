import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters with sensible defaults tuned for SIFT1M
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.train_samples = int(kwargs.get("train_samples", 200000))
        self.seed = int(kwargs.get("seed", 1234))
        self.threads = int(kwargs.get("threads", max(1, faiss.omp_get_max_threads())))
        self.add_block_size = int(kwargs.get("add_block_size", 131072))
        self.use_flat_fallback_threshold = int(kwargs.get("flat_threshold", 50000))

        faiss.omp_set_num_threads(self.threads)

        self.index = None
        self.ntotal = 0
        self._rng = np.random.RandomState(self.seed)
        self._is_trained = False
        self._use_flat = False

    def _build_ivf_index(self):
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        return index

    def _build_flat_index(self):
        return faiss.IndexFlatL2(self.dim)

    def add(self, xb: np.ndarray) -> None:
        if xb is None or len(xb) == 0:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        n, d = xb.shape
        if d != self.dim:
            raise ValueError(f"Input dimension {d} does not match index dimension {self.dim}")

        # Choose index type if not created yet
        if self.index is None:
            # For small datasets, fall back to flat for simplicity and perfect recall
            if n < self.use_flat_fallback_threshold:
                self.index = self._build_flat_index()
                self._use_flat = True
                self._is_trained = True
            else:
                self.index = self._build_ivf_index()

        # Train if needed (IVF only)
        if not self._use_flat and not self._is_trained:
            train_n = min(self.train_samples, n)
            # Sample without replacement for training
            if train_n < n:
                train_idx = self._rng.choice(n, size=train_n, replace=False)
                xtrain = xb[train_idx]
            else:
                xtrain = xb
            self.index.train(xtrain)
            self._is_trained = True
            if hasattr(self.index, "nprobe"):
                self.index.nprobe = self.nprobe

        # Add in blocks to manage memory
        start = 0
        while start < n:
            end = min(start + self.add_block_size, n)
            self.index.add(xb[start:end])
            self.ntotal += (end - start)
            start = end

        # Ensure search params are set
        if hasattr(self.index, "nprobe"):
            self.index.nprobe = self.nprobe

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or self.ntotal == 0:
            raise RuntimeError("Index is empty. Call add() before search().")
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        nq, d = xq.shape
        if d != self.dim:
            raise ValueError(f"Query dimension {d} does not match index dimension {self.dim}")
        if k <= 0:
            raise ValueError("k must be positive")
        if k > max(1, self.ntotal):
            k = max(1, self.ntotal)

        faiss.omp_set_num_threads(self.threads)
        if hasattr(self.index, "nprobe"):
            self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, k)

        # Ensure correct dtypes and shapes
        if not isinstance(D, np.ndarray):
            D = np.array(D, dtype=np.float32)
        if not isinstance(I, np.ndarray):
            I = np.array(I, dtype=np.int64)

        D = np.ascontiguousarray(D, dtype=np.float32).reshape(nq, k)
        I = np.ascontiguousarray(I, dtype=np.int64).reshape(nq, k)
        return D, I
