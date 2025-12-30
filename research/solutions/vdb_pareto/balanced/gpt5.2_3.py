import os
from typing import Tuple, List, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.threads = int(kwargs.get("threads", min(8, (os.cpu_count() or 1))))
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 512))

        self.train_size = int(kwargs.get("train_size", 400000))
        self.niter = int(kwargs.get("niter", 25))
        self.max_points_per_centroid = int(kwargs.get("max_points_per_centroid", 0))

        self._pending: List[np.ndarray] = []
        self._pending_n = 0

        self._flat_fallback = None
        self._ntotal = 0

        if faiss is None:
            self._flat_fallback = True
            self.xb = None
            return

        faiss.omp_set_num_threads(self.threads)

        quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

        try:
            self.index.cp.niter = self.niter
            if self.max_points_per_centroid > 0:
                self.index.cp.max_points_per_centroid = self.max_points_per_centroid
        except Exception:
            pass

    def _as_f32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _train_from_pending(self) -> None:
        if faiss is None:
            return
        if self.index.is_trained:
            return
        if self._pending_n < max(self.nlist, 2 * self.nlist):
            return

        ts = min(self.train_size, self._pending_n)
        train_x = np.empty((ts, self.dim), dtype=np.float32)

        filled = 0
        for arr in self._pending:
            if filled >= ts:
                break
            take = min(arr.shape[0], ts - filled)
            train_x[filled : filled + take] = arr[:take]
            filled += take

        if filled < ts:
            train_x = train_x[:filled]

        self.index.train(train_x)

        for arr in self._pending:
            self.index.add(arr)
            self._ntotal += arr.shape[0]

        self._pending.clear()
        self._pending_n = 0

    def _ensure_ready(self) -> None:
        if faiss is None:
            return

        if not self.index.is_trained:
            if self._pending_n >= max(self.nlist, 2 * self.nlist):
                self._train_from_pending()
            else:
                self._flat_fallback = faiss.IndexFlatL2(self.dim)
                if self._pending_n > 0:
                    for arr in self._pending:
                        self._flat_fallback.add(arr)
                        self._ntotal += arr.shape[0]
                self._pending.clear()
                self._pending_n = 0

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_f32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is None:
            if self.xb is None:
                self.xb = xb.copy()
            else:
                self.xb = np.vstack([self.xb, xb])
            return

        faiss.omp_set_num_threads(self.threads)

        if self._flat_fallback is not None and self._flat_fallback is not True:
            self._flat_fallback.add(xb)
            self._ntotal += xb.shape[0]
            return

        if not self.index.is_trained:
            self._pending.append(xb)
            self._pending_n += xb.shape[0]
            if self._pending_n >= max(self.train_size, self.nlist * 16):
                self._train_from_pending()
            return

        self.index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be > 0")

        xq = self._as_f32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if faiss is None:
            xb = self.xb
            if xb is None or xb.shape[0] == 0:
                D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
                I = np.full((xq.shape[0], k), -1, dtype=np.int64)
                return D, I
            xq2 = (xq * xq).sum(axis=1, keepdims=True)
            xb2 = (xb * xb).sum(axis=1, keepdims=True).T
            dist = xq2 + xb2 - 2.0 * (xq @ xb.T)
            idx = np.argpartition(dist, kth=min(k - 1, dist.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(xq.shape[0])[:, None]
            dsel = dist[row, idx]
            order = np.argsort(dsel, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dsel[row, order].astype(np.float32, copy=False)
            return D, I

        faiss.omp_set_num_threads(self.threads)

        self._ensure_ready()

        if self._flat_fallback is not None and self._flat_fallback is not True:
            D, I = self._flat_fallback.search(xq, k)
            return D, I

        self.index.nprobe = self.nprobe
        D, I = self.index.search(xq, k)
        return D, I