import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs,
    ):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", kwargs.get("n_probes", kwargs.get("ef_search", 64))))
        self.train_size = int(kwargs.get("train_size", 200_000))
        self.min_train_size = int(kwargs.get("min_train_size", max(50_000, min(250_000, self.nlist * 40))))
        self.num_threads = int(kwargs.get("num_threads", min(8, os.cpu_count() or 8)))

        self._use_faiss = faiss is not None
        self._trained = False
        self._pending = []
        self._pending_count = 0

        if self._use_faiss:
            faiss.omp_set_num_threads(self.num_threads)

            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            try:
                self.index.cp.niter = int(kwargs.get("kmeans_niter", 20))
                self.index.cp.seed = int(kwargs.get("seed", 123))
                self.index.cp.verbose = False
                self.index.cp.min_points_per_centroid = int(kwargs.get("min_points_per_centroid", 10))
            except Exception:
                pass
            self.index.nprobe = self.nprobe
            try:
                self.index.parallel_mode = int(kwargs.get("parallel_mode", 1))
            except Exception:
                pass
        else:  # pragma: no cover
            self.index = None
            self._xb = None

    def _ensure_float32_c(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x, dtype=np.float32)
        return x

    def _train_from(self, xb: np.ndarray) -> None:
        if not self._use_faiss or self._trained:
            return

        xb = self._ensure_float32_c(xb)
        n = xb.shape[0]
        if n <= 0:
            return

        ntrain = min(self.train_size, n)
        if ntrain < self.min_train_size and n >= self.min_train_size:
            ntrain = self.min_train_size

        if ntrain <= 0:
            return

        step = max(1, n // ntrain)
        xt = xb[::step]
        if xt.shape[0] > ntrain:
            xt = xt[:ntrain]
        xt = self._ensure_float32_c(xt)

        self.index.train(xt)
        self._trained = True
        self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        xb = self._ensure_float32_c(xb)

        if not self._use_faiss:  # pragma: no cover
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            return

        if not self._trained:
            if xb.shape[0] >= self.min_train_size:
                self._train_from(xb)
                self.index.add(xb)
                return
            else:
                self._pending.append(xb)
                self._pending_count += xb.shape[0]
                if self._pending_count >= self.min_train_size:
                    buf = np.vstack(self._pending) if len(self._pending) > 1 else self._pending[0]
                    self._pending = []
                    self._pending_count = 0
                    self._train_from(buf)
                    self.index.add(buf)
                return

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        xq = self._ensure_float32_c(xq)

        if not self._use_faiss:  # pragma: no cover
            if self._xb is None or self._xb.shape[0] == 0:
                D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
                I = np.full((xq.shape[0], k), -1, dtype=np.int64)
                return D, I
            xb = self._xb
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
            sims = xq @ xb.T
            d2 = xq_norm + xb_norm - 2.0 * sims
            idx = np.argpartition(d2, kth=min(k - 1, d2.shape[1] - 1), axis=1)[:, :k]
            dsel = d2[np.arange(d2.shape[0])[:, None], idx]
            order = np.argsort(dsel, axis=1)
            I = idx[np.arange(idx.shape[0])[:, None], order].astype(np.int64, copy=False)
            D = dsel[np.arange(dsel.shape[0])[:, None], order].astype(np.float32, copy=False)
            return D, I

        if self._pending_count > 0 and not self._trained:
            buf = np.vstack(self._pending) if len(self._pending) > 1 else self._pending[0]
            self._pending = []
            self._pending_count = 0
            self._train_from(buf)
            if self._trained:
                self.index.add(buf)

        self.index.nprobe = self.nprobe
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I