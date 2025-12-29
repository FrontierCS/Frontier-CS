import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 24))

        self.max_train = int(kwargs.get("max_train", 200000))
        self.min_train = int(kwargs.get("min_train", max(20000, self.nlist * 20)))
        self.kmeans_niter = int(kwargs.get("kmeans_niter", 15))
        self.kmeans_seed = int(kwargs.get("kmeans_seed", 123))

        self.n_threads = int(kwargs.get("n_threads", min(8, os.cpu_count() or 1)))

        self._index = None
        self._ntotal = 0
        self._rng = np.random.default_rng(self.kmeans_seed)

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

    def _ensure_faiss_index(self, n_first_add: int) -> None:
        if self._index is not None:
            return
        if faiss is None:
            self._index = "numpy_fallback"
            return

        nlist = self.nlist
        if n_first_add > 0 and n_first_add < nlist:
            nlist = max(1, min(nlist, max(1, n_first_add // 50)))
        self.nlist = nlist
        if self.nprobe > self.nlist:
            self.nprobe = self.nlist

        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        try:
            index.nprobe = self.nprobe
        except Exception:
            pass

        try:
            index.parallel_mode = 2
        except Exception:
            pass

        try:
            cp = index.cp
            cp.niter = self.kmeans_niter
            cp.seed = self.kmeans_seed
            cp.verbose = False
        except Exception:
            pass

        self._index = index

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        self._ensure_faiss_index(xb.shape[0])

        if self._index == "numpy_fallback":
            if not hasattr(self, "_xb"):
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            self._ntotal = int(self._xb.shape[0])
            return

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

        if not self._index.is_trained:
            n = xb.shape[0]
            train_size = min(self.max_train, n)
            train_size = max(train_size, min(n, self.min_train))

            if train_size < n:
                idx = self._rng.choice(n, size=train_size, replace=False)
                xt = np.ascontiguousarray(xb[idx], dtype=np.float32)
            else:
                xt = xb

            self._index.train(xt)

        self._index.add(xb)
        self._ntotal = int(self._index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            xq = np.asarray(xq)
            nq = int(xq.shape[0]) if xq.ndim > 0 else 0
            return (
                np.empty((nq, 0), dtype=np.float32),
                np.empty((nq, 0), dtype=np.int64),
            )

        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        nq = int(xq.shape[0])

        if self._ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        if self._index == "numpy_fallback":
            xb = self._xb
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1)[None, :]
            Dall = xq_norm + xb_norm - 2.0 * (xq @ xb.T)
            kk = min(int(k), int(xb.shape[0]))
            I = np.argpartition(Dall, kk - 1, axis=1)[:, :kk]
            Dsel = Dall[np.arange(nq)[:, None], I]
            order = np.argsort(Dsel, axis=1)
            I = I[np.arange(nq)[:, None], order]
            D = Dsel[np.arange(nq)[:, None], order].astype(np.float32, copy=False)
            if kk < k:
                Ipad = np.full((nq, k - kk), -1, dtype=np.int64)
                Dpad = np.full((nq, k - kk), np.inf, dtype=np.float32)
                I = np.hstack([I.astype(np.int64, copy=False), Ipad])
                D = np.hstack([D, Dpad])
            else:
                I = I.astype(np.int64, copy=False)
            return D, I

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

        try:
            self._index.nprobe = min(self.nprobe, self.nlist)
        except Exception:
            pass

        D, I = self._index.search(xq, int(k))

        if I.shape[1] != k:
            I2 = np.full((nq, k), -1, dtype=np.int64)
            D2 = np.full((nq, k), np.inf, dtype=np.float32)
            kk = min(I.shape[1], k)
            I2[:, :kk] = I[:, :kk]
            D2[:, :kk] = D[:, :kk].astype(np.float32, copy=False)
            return D2, I2

        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)