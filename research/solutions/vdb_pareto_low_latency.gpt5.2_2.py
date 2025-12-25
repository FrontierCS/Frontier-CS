import os
from typing import Tuple, Optional, List

import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.train_size = int(kwargs.get("train_size", 120000))
        self.niter = int(kwargs.get("niter", 12))
        self.seed = int(kwargs.get("seed", 123))
        self.add_batch_size = int(kwargs.get("add_batch_size", 200000))

        n_threads = kwargs.get("n_threads", None)
        if n_threads is None:
            n_threads = os.cpu_count() or 1
        self.n_threads = int(max(1, min(8, n_threads)))

        self._index = None
        self._pending: List[np.ndarray] = []
        self._pending_rows = 0
        self._trained = False

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

    def _ensure_faiss(self):
        if faiss is None:
            raise RuntimeError("faiss is required but could not be imported.")

    def _make_index(self):
        self._ensure_faiss()
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        try:
            index.cp.niter = self.niter
        except Exception:
            pass
        try:
            index.cp.seed = self.seed
        except Exception:
            pass
        try:
            index.cp.max_points_per_centroid = 256
        except Exception:
            pass
        try:
            index.cp.min_points_per_centroid = 5
        except Exception:
            pass
        index.nprobe = self.nprobe
        return index

    def _train_if_needed(self):
        if self._trained:
            return
        if self._index is None:
            self._index = self._make_index()
        if self._pending_rows <= max(self.nlist * 10, self.nlist + 1, 20000):
            return

        xb_all = np.vstack(self._pending)
        n = xb_all.shape[0]

        ts = min(self.train_size, n)
        if ts < self.nlist + 1:
            ts = min(n, self.nlist + 1)

        if ts < n:
            step = max(1, n // ts)
            xtrain = xb_all[::step][:ts]
        else:
            xtrain = xb_all

        xtrain = np.ascontiguousarray(xtrain, dtype=np.float32)
        try:
            faiss.omp_set_num_threads(self.n_threads)
        except Exception:
            pass
        self._index.train(xtrain)
        self._trained = True

        self._add_to_index(xb_all)
        self._pending.clear()
        self._pending_rows = 0

    def _add_to_index(self, xb: np.ndarray) -> None:
        if xb.size == 0:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        try:
            faiss.omp_set_num_threads(self.n_threads)
        except Exception:
            pass
        n = xb.shape[0]
        bs = self.add_batch_size
        if bs <= 0 or bs >= n:
            self._index.add(xb)
            return
        for i in range(0, n, bs):
            self._index.add(xb[i : i + bs])

    def add(self, xb: np.ndarray) -> None:
        self._ensure_faiss()
        if xb is None or xb.size == 0:
            return
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if self._index is None:
            self._index = self._make_index()

        if not self._trained:
            self._pending.append(np.ascontiguousarray(xb))
            self._pending_rows += xb.shape[0]
            self._train_if_needed()
            return

        self._add_to_index(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self._ensure_faiss()
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        if xq is None or xq.size == 0:
            return (
                np.empty((0, k), dtype=np.float32),
                np.empty((0, k), dtype=np.int64),
            )

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if self._index is None:
            D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
            I = np.full((xq.shape[0], k), -1, dtype=np.int64)
            return D, I

        if not self._trained:
            if self._pending_rows > 0:
                self._train_if_needed()
            if not self._trained:
                D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
                I = np.full((xq.shape[0], k), -1, dtype=np.int64)
                return D, I

        try:
            faiss.omp_set_num_threads(self.n_threads)
        except Exception:
            pass

        self._index.nprobe = self.nprobe
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        D, I = self._index.search(xq, k)
        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)