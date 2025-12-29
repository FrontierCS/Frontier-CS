import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception as _e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 1536))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.niter = int(kwargs.get("niter", 15))

        omp_threads = kwargs.get("omp_threads", None)
        if omp_threads is None:
            omp_threads = min(8, os.cpu_count() or 1)
        self.omp_threads = int(omp_threads)

        if faiss is None:
            self._xb = None
            return

        faiss.omp_set_num_threads(self.omp_threads)

        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        try:
            self.index.cp.niter = self.niter
            self.index.cp.min_points_per_centroid = 5
            self.index.cp.max_points_per_centroid = 100000000
        except Exception:
            pass

        self.index.nprobe = min(self.nprobe, self.nlist)

        self._pending = []
        self._pending_n = 0

    def _as_contig_f32(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _make_train_sample(self, xb: np.ndarray) -> np.ndarray:
        n = xb.shape[0]
        target = max(self.nlist, min(self.train_size, n))
        if n <= target:
            return xb
        rng = np.random.default_rng(12345)
        idx = rng.choice(n, size=target, replace=False)
        return xb[idx]

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_contig_f32(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is None:
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            return

        if self.index.is_trained:
            self.index.add(xb)
            return

        self._pending.append(xb)
        self._pending_n += xb.shape[0]

        if self._pending_n < self.nlist:
            return

        if len(self._pending) == 1:
            train_x = self._make_train_sample(self._pending[0])
        else:
            total = self._pending_n
            target = max(self.nlist, self.train_size)
            target = min(target, total)

            rng = np.random.default_rng(12345)
            parts = []
            remaining = target
            for i, a in enumerate(self._pending):
                if remaining <= 0:
                    break
                n = a.shape[0]
                if i == len(self._pending) - 1:
                    take = remaining
                else:
                    take = int(round(target * (n / total)))
                    take = max(0, min(take, remaining))
                if take <= 0:
                    continue
                if take >= n:
                    parts.append(a)
                else:
                    idx = rng.choice(n, size=take, replace=False)
                    parts.append(a[idx])
                remaining -= take
            if not parts:
                train_x = self._make_train_sample(self._pending[0])
            else:
                train_x = np.ascontiguousarray(np.vstack(parts), dtype=np.float32)

        self.index.train(train_x)

        for a in self._pending:
            self.index.add(a)
        self._pending.clear()
        self._pending_n = 0

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            xq = self._as_contig_f32(xq)
            nq = xq.shape[0]
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        xq = self._as_contig_f32(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if faiss is None:
            xb = self._xb
            if xb is None or xb.shape[0] == 0:
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

            xq2 = np.sum(xq * xq, axis=1, keepdims=True).astype(np.float32, copy=False)
            xb2 = np.sum(xb * xb, axis=1, keepdims=True).astype(np.float32, copy=False).T
            dots = xq @ xb.T
            d2 = xq2 + xb2 - 2.0 * dots
            if k == 1:
                idx = np.argmin(d2, axis=1).astype(np.int64)
                dist = d2[np.arange(d2.shape[0]), idx].astype(np.float32, copy=False)
                return dist.reshape(-1, 1), idx.reshape(-1, 1)
            idx_part = np.argpartition(d2, kth=k - 1, axis=1)[:, :k]
            row = np.arange(d2.shape[0])[:, None]
            d_part = d2[row, idx_part]
            order = np.argsort(d_part, axis=1)
            idx = idx_part[row, order].astype(np.int64, copy=False)
            dist = d2[row, idx].astype(np.float32, copy=False)
            return dist, idx

        if not self.index.is_trained:
            if self._pending_n > 0:
                for a in self._pending:
                    self.index.add(a)
                self._pending.clear()
                self._pending_n = 0
            else:
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        self.index.nprobe = min(self.nprobe, self.nlist)
        D, I = self.index.search(xq, k)

        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)

        if np.any(I < 0):
            nt = self.index.ntotal
            if nt > 0:
                I = np.where(I < 0, 0, I)
                D = np.where(D < 0, np.float32(np.inf), D)
            else:
                I.fill(-1)
                D.fill(np.float32(np.inf))

        return D, I