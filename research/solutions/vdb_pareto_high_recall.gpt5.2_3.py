import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.threads = int(kwargs.get("threads", max(1, min(8, os.cpu_count() or 1))))
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 2048))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.niter = int(kwargs.get("niter", 15))
        self.seed = int(kwargs.get("seed", 12345))

        self._ntotal_added = 0
        self._rng = np.random.default_rng(self.seed)

        if faiss is None:
            self._xb = None
            return

        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        try:
            self.index.cp.niter = self.niter
            self.index.cp.verbose = False
        except Exception:
            pass

        self.index.nprobe = max(1, min(self.nprobe, self.nlist))

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is None:
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack((self._xb, xb))
            self._ntotal_added = int(self._xb.shape[0])
            return

        if not self.index.is_trained:
            n = int(xb.shape[0])
            if n < self.nlist:
                new_nlist = max(1, min(self.nlist, 2 ** int(np.floor(np.log2(max(2, n))))))
                if new_nlist != self.nlist:
                    self.nlist = int(new_nlist)
                    self.quantizer = faiss.IndexFlatL2(self.dim)
                    self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
                    try:
                        self.index.cp.niter = self.niter
                        self.index.cp.verbose = False
                    except Exception:
                        pass
                    self.index.nprobe = max(1, min(self.nprobe, self.nlist))

            n_train = min(self.train_size, n)
            if n_train < self.nlist:
                n_train = n

            if n_train == n:
                xt = xb
            else:
                idx = self._rng.choice(n, size=n_train, replace=False)
                xt = np.ascontiguousarray(xb[idx], dtype=np.float32)

            self.index.train(xt)

        self.index.add(xb)
        self._ntotal_added += int(xb.shape[0])

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        nq = int(xq.shape[0])
        if nq == 0:
            return (
                np.empty((0, k), dtype=np.float32),
                np.empty((0, k), dtype=np.int64),
            )

        if faiss is None:
            if self._xb is None or self._xb.shape[0] == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            xb = self._xb
            xb_norm = (xb * xb).sum(axis=1, keepdims=False)
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            G = xq @ xb.T
            D2 = xq_norm + xb_norm[None, :] - 2.0 * G
            np.maximum(D2, 0.0, out=D2)

            if k == 1:
                I = np.argmin(D2, axis=1).astype(np.int64)[:, None]
                D = D2[np.arange(nq), I[:, 0]].astype(np.float32)[:, None]
                return D, I

            idx_part = np.argpartition(D2, kth=k - 1, axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            d_part = D2[row, idx_part]
            order = np.argsort(d_part, axis=1)
            I = idx_part[row, order].astype(np.int64)
            D = D2[row, I].astype(np.float32)
            return D, I

        if not self.index.is_trained or self.index.ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        self.index.nprobe = max(1, min(self.nprobe, self.nlist))
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I