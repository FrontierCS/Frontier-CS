import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception:
    faiss = None


def _as_f32_c(x: np.ndarray) -> np.ndarray:
    if x is None:
        return x
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    if not x.flags["C_CONTIGUOUS"]:
        x = np.ascontiguousarray(x)
    return x


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 3))
        self.n_threads = int(kwargs.get("n_threads", min(8, (os.cpu_count() or 1))))

        self._xb_fallback: Optional[np.ndarray] = None

        self.index = None
        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

            try:
                self.index = faiss.index_factory(self.dim, f"IVF{self.nlist},PQ{self.m}x{self.nbits}", faiss.METRIC_L2)
            except Exception:
                quantizer = faiss.IndexFlatL2(self.dim)
                self.index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)

            try:
                self.index.nprobe = self.nprobe
            except Exception:
                pass

            try:
                if hasattr(self.index, "parallel_mode"):
                    self.index.parallel_mode = 1
            except Exception:
                pass

            try:
                if hasattr(self.index, "use_precomputed_table"):
                    self.index.use_precomputed_table = 1
            except Exception:
                pass

            try:
                if hasattr(self.index, "polysemous_ht"):
                    self.index.polysemous_ht = 0
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        xb = _as_f32_c(xb)
        if xb is None or xb.size == 0:
            return
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if self.index is None:
            if self._xb_fallback is None:
                self._xb_fallback = xb.copy()
            else:
                self._xb_fallback = np.vstack((self._xb_fallback, xb))
            return

        if not self.index.is_trained:
            n = xb.shape[0]
            target = int(min(200000, n))
            min_needed = int(max(10000, 32 * self.nlist))
            target = int(max(min_needed, target))
            if target > n:
                target = n
            step = max(1, n // target)
            xtr = xb[::step][:target]
            xtr = _as_f32_c(xtr)
            self.index.train(xtr)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            nq = 0 if xq is None else int(xq.shape[0])
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        xq = _as_f32_c(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        nq = xq.shape[0]

        if self.index is None:
            if self._xb_fallback is None or self._xb_fallback.size == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._xb_fallback
            xb = _as_f32_c(xb)
            qn = (xq * xq).sum(axis=1, keepdims=True)
            bn = (xb * xb).sum(axis=1, keepdims=True).T
            sims = xq @ xb.T
            dist = qn + bn - 2.0 * sims
            idx = np.argpartition(dist, kth=min(k - 1, dist.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dd = dist[row, idx]
            order = np.argsort(dd, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dd[row, order].astype(np.float32, copy=False)
            return D, I

        try:
            if hasattr(self.index, "nprobe"):
                self.index.nprobe = self.nprobe
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.shape != (nq, k) or I.shape != (nq, k):
            D = np.ascontiguousarray(D.reshape(nq, k).astype(np.float32, copy=False))
            I = np.ascontiguousarray(I.reshape(nq, k).astype(np.int64, copy=False))
        return D, I