import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


def _as_float32_contig(x: np.ndarray) -> np.ndarray:
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    if not x.flags["C_CONTIGUOUS"]:
        x = np.ascontiguousarray(x)
    return x


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        if faiss is None:
            raise ImportError("faiss is required for this solution")

        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 192))
        self.train_size = int(kwargs.get("train_size", 200_000))
        self.n_threads = int(kwargs.get("n_threads", min(8, os.cpu_count() or 1)))

        self._index = None
        self._trained = False
        self._ntotal = 0

        faiss.omp_set_num_threads(self.n_threads)

    def _build_and_train(self, xb: np.ndarray) -> None:
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        try:
            cp = index.cp
            cp.niter = int(getattr(cp, "niter", 20))
            cp.verbose = False
        except Exception:
            pass

        index.nprobe = self.nprobe

        n = xb.shape[0]
        if n <= self.train_size:
            xt = xb
        else:
            step = max(1, n // self.train_size)
            xt = xb[0 : step * self.train_size : step]

        if xt.shape[0] < self.nlist:
            xt = xb[: min(n, max(self.nlist, 10_000))]

        index.train(xt)
        self._index = index
        self._trained = True

    def add(self, xb: np.ndarray) -> None:
        xb = _as_float32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if not self._trained:
            self._build_and_train(xb)

        self._index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._index is None or not self._trained:
            raise RuntimeError("Index not trained/initialized. Call add() first.")

        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        xq = _as_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if self._index.nprobe != self.nprobe:
            self._index.nprobe = self.nprobe

        D, I = self._index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I