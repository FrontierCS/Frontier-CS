import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 512))
        self.n_train = int(kwargs.get("n_train", 200000))
        self.seed = int(kwargs.get("seed", 123))
        self.threads = int(kwargs.get("threads", min(8, (os.cpu_count() or 1))))

        self._trained = False
        self._ntotal_added = 0

        if faiss is None:
            self._xb = None
            return

        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = min(self.nprobe, self.nlist)

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")
        if xb.size == 0:
            return
        xb = np.ascontiguousarray(xb)

        if faiss is None:
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            self._ntotal_added = int(self._xb.shape[0])
            return

        if not self._trained:
            n = xb.shape[0]
            n_train = min(self.n_train, n)
            if n_train < self.nlist:
                n_train = min(n, max(self.nlist, n_train))
            rs = np.random.RandomState(self.seed)
            if n_train == n:
                train_x = xb
            else:
                idx = rs.choice(n, size=n_train, replace=False)
                train_x = xb[idx]
            self.index.train(train_x)
            self._trained = True
            self.index.nprobe = min(self.nprobe, self.nlist)

        self.index.add(xb)
        self._ntotal_added += int(xb.shape[0])

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")
        nq = int(xq.shape[0])
        xq = np.ascontiguousarray(xq)

        if nq == 0:
            return np.empty((0, k), dtype=np.float32), np.empty((0, k), dtype=np.int64)

        if faiss is None:
            if self._xb is None or self._xb.shape[0] == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._xb
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
            d2 = xq_norm + xb_norm - 2.0 * (xq @ xb.T)
            idx = np.argpartition(d2, kth=min(k - 1, d2.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dd = d2[row, idx]
            ord_ = np.argsort(dd, axis=1)
            I = idx[row, ord_].astype(np.int64, copy=False)
            D = dd[row, ord_].astype(np.float32, copy=False)
            return D, I

        if not self._trained or self.index.ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        self.index.nprobe = min(self.nprobe, self.nlist)
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I