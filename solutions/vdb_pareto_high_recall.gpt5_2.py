import os
import numpy as np
from typing import Tuple, Optional

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs
    ):
        """
        Initialize an IVF-Flat FAISS index tuned for high recall under a relaxed latency budget.
        """
        if faiss is None:
            raise RuntimeError("faiss is required for this solution.")
        self.dim = dim

        # Parameters (tuned for high recall within latency budget)
        self.nlist: int = int(kwargs.get("nlist", 16384))          # number of Voronoi cells
        self.nprobe: int = int(kwargs.get("nprobe", 256))          # cells to probe at search
        self.train_size: int = int(kwargs.get("train_size", 262144))  # training sample size
        self.threads: int = int(kwargs.get("threads", max(1, os.cpu_count() or 1)))
        self.seed: Optional[int] = kwargs.get("seed", 12345)

        # Setup FAISS threading
        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        # Quantizer and IVF-Flat index
        quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        # Set nprobe via both attribute and ParameterSpace for compatibility
        try:
            self.index.nprobe = self.nprobe
        except Exception:
            pass
        try:
            ps = faiss.ParameterSpace()
            ps.set_index_parameter(self.index, "nprobe", self.nprobe)
        except Exception:
            pass

        # Track number of vectors added
        self.ntotal = 0

        # Seed RNG for reproducibility in training sampling
        self._rng = np.random.RandomState(self.seed) if self.seed is not None else np.random

    def _ensure_trained(self, xb: np.ndarray) -> None:
        if self.index.is_trained:
            return
        # Ensure training with sufficient samples (at least nlist)
        n = xb.shape[0]
        train_sz = min(n, max(self.train_size, self.nlist))
        if train_sz < self.nlist:
            # As a fallback, if incoming batch is too small to train, defer training to later add
            # but for SIFT1M this should not happen; still handle defensively.
            self.index.train(xb.astype(np.float32, copy=False))
            return
        if train_sz == n:
            xb_train = xb.astype(np.float32, copy=False)
        else:
            idx = self._rng.choice(n, size=train_sz, replace=False)
            xb_train = xb[idx].astype(np.float32, copy=False)

        self.index.train(xb_train)

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            raise TypeError("xb must be a numpy.ndarray")
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        # Train if needed
        self._ensure_trained(xb)

        # Add vectors
        self.index.add(xb)
        self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            raise TypeError("xq must be a numpy.ndarray")
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")
        if k <= 0:
            raise ValueError("k must be positive")
        if self.ntotal == 0:
            # No data; return empty results with -1 indices and +inf distances
            nq = xq.shape[0]
            return (np.full((nq, k), np.inf, dtype=np.float32),
                    np.full((nq, k), -1, dtype=np.int64))

        # Ensure threads
        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        # Ensure nprobe is set (in case user mutated it after init)
        try:
            self.index.nprobe = self.nprobe
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        # Ensure numpy arrays with correct dtypes and shapes
        if not isinstance(D, np.ndarray):
            D = np.array(D, dtype=np.float32)
        if not isinstance(I, np.ndarray):
            I = np.array(I, dtype=np.int64)
        return D, I
