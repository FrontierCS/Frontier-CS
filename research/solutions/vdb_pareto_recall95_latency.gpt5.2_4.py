import os
from typing import Tuple, Optional, List

import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", kwargs.get("ef_search", 96)))
        self.train_size = int(kwargs.get("train_size", 200_000))
        self.min_train_points = int(kwargs.get("min_train_points", max(10_000, self.nlist * 20)))
        self.threads = int(kwargs.get("threads", min(8, os.cpu_count() or 1)))
        self.metric = kwargs.get("metric", "l2")

        if faiss is None:
            raise RuntimeError("faiss is required for this solution but could not be imported.")

        if self.metric not in ("l2", "L2", faiss.METRIC_L2):
            raise ValueError("Only L2 metric is supported.")

        faiss.omp_set_num_threads(self.threads)

        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

        self._pending: List[np.ndarray] = []
        self._pending_rows: int = 0
        self._trained: bool = False

    def _maybe_train(self) -> None:
        if self._trained or self.index.is_trained:
            self._trained = True
            return
        if self._pending_rows < self.min_train_points:
            return

        if len(self._pending) == 1:
            xall = self._pending[0]
        else:
            xall = np.vstack(self._pending)

        n = xall.shape[0]
        ts = min(self.train_size, n)
        if ts < self.nlist:
            ts = n
        if ts < self.nlist:
            return

        if ts == n:
            train_x = xall
        else:
            rs = np.random.RandomState(12345)
            idx = rs.choice(n, size=ts, replace=False)
            train_x = xall[idx]

        train_x = np.ascontiguousarray(train_x, dtype=np.float32)
        self.index.train(train_x)
        self._trained = True

        for chunk in self._pending:
            self.index.add(chunk)
        self._pending.clear()
        self._pending_rows = 0

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if self._trained or self.index.is_trained:
            self._trained = True
            self.index.add(xb)
            return

        self._pending.append(xb)
        self._pending_rows += xb.shape[0]
        self._maybe_train()

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            raise ValueError("k must be >= 1")
        if not (self._trained or self.index.is_trained):
            self._maybe_train()
        if not (self._trained or self.index.is_trained):
            raise RuntimeError("Index is not trained; add more vectors before searching.")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        D, I = self.index.search(xq, int(k))
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I