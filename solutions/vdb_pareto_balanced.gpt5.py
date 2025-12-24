import os
from typing import Tuple
import numpy as np

try:
    import faiss
except ImportError as e:
    raise RuntimeError("faiss-cpu is required for this solution") from e


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 128))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.refine_k = int(kwargs.get("refine_k", 2))
        self.seed = int(kwargs.get("seed", 123))
        self.num_threads = int(kwargs.get("num_threads", os.cpu_count() or 8))

        faiss.omp_set_num_threads(self.num_threads)

        self._rng = np.random.RandomState(self.seed)

        self.base_index = None  # underlying IVF index
        self.index = None       # possibly wrapped with refine
        self._is_trained = False
        self.ntotal = 0

    def _build_index(self):
        quantizer = faiss.IndexFlatL2(self.dim)
        ivf = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        if self.refine_k > 1:
            refine = faiss.IndexRefineFlat(ivf)
            refine.k_factor = self.refine_k
            self.base_index = ivf
            self.index = refine
        else:
            self.base_index = ivf
            self.index = ivf
        self.base_index.nprobe = max(1, self.nprobe)

    def _ensure_index(self):
        if self.index is None:
            self._build_index()

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)
        if xb.shape[1] != self.dim:
            raise ValueError("Input vectors have incorrect dimensionality")

        self._ensure_index()

        if not self._is_trained:
            n = xb.shape[0]
            n_train = min(self.train_size, n)
            if n_train < self.nlist:
                n_train = min(n, max(self.nlist, self.nlist))  # ensure >= nlist
            if n_train == n:
                xt = xb
            else:
                idx = self._rng.choice(n, size=n_train, replace=False)
                xt = xb[idx]
            self.index.train(xt)
            self._is_trained = True

        self.index.add(xb)
        self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)
        if xq.shape[1] != self.dim:
            raise ValueError("Query vectors have incorrect dimensionality")

        if self.index is None or not self._is_trained or self.ntotal == 0:
            # Return empty results if not ready
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # Ensure thread setting and nprobe are applied
        faiss.omp_set_num_threads(self.num_threads)
        self.base_index.nprobe = max(1, self.nprobe)

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
