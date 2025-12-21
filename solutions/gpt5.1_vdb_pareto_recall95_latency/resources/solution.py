import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Optional kwargs:
            - index_key: faiss index_factory description string. Default: "IVF2048,Flat"
            - nlist: number of IVF lists (used if index_key not provided). Default: 2048
            - nprobe: number of IVF probes at search time. Default: 256
            - train_size: number of vectors to sample for IVF training. Default: 100000
            - num_threads: number of FAISS OMP threads. Default: min(8, omp_get_max_threads())
        """
        self.dim = dim
        self.metric = faiss.METRIC_L2

        index_key = kwargs.get("index_key", None)
        if index_key is None:
            nlist = int(kwargs.get("nlist", 2048))
            index_key = f"IVF{nlist},Flat"
        self.index_key = index_key

        self.nprobe = int(kwargs.get("nprobe", 256))
        self.train_size = int(kwargs.get("train_size", 100000))

        self.index = None

        # Configure FAISS threading (use up to 8 threads by default)
        num_threads = kwargs.get("num_threads", None)
        try:
            if num_threads is None:
                max_threads = faiss.omp_get_max_threads()
                if max_threads is not None and max_threads > 0:
                    num_threads = min(8, max_threads)
            if num_threads is not None:
                faiss.omp_set_num_threads(int(num_threads))
        except Exception:
            # If FAISS threading configuration fails, ignore and proceed with defaults
            pass

    def _ensure_index(self) -> None:
        if self.index is None:
            self.index = faiss.index_factory(self.dim, self.index_key, self.metric)
            if hasattr(self.index, "nprobe"):
                self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")
        xb = np.ascontiguousarray(xb)

        self._ensure_index()

        # Train the index if needed (IVF, etc.)
        if not self.index.is_trained:
            n_train = min(self.train_size, xb.shape[0])
            if xb.shape[0] > n_train:
                try:
                    rng = np.random.default_rng()
                    idx = rng.choice(xb.shape[0], size=n_train, replace=False)
                except AttributeError:
                    idx = np.random.choice(xb.shape[0], size=n_train, replace=False)
                x_train = xb[idx].copy()
            else:
                x_train = xb.copy()
            self.index.train(x_train)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")
        xq = np.ascontiguousarray(xq)

        if self.index is None or self.index.ntotal == 0:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = -np.ones((nq, k), dtype=np.int64)
            return D, I

        if hasattr(self.index, "nprobe"):
            self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I
