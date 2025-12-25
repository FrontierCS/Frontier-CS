import os
import math
import numpy as np
from typing import Tuple, Optional

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None  # type: ignore


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.n_threads = int(kwargs.get("n_threads", kwargs.get("threads", 8)))
        self.nlist = int(kwargs.get("nlist", 16384))
        self.nprobe = int(kwargs.get("nprobe", 96))

        self.train_niter = int(kwargs.get("niter", 20))
        self.train_nredo = int(kwargs.get("nredo", 1))
        self.train_size = kwargs.get("train_size", None)
        self.train_min_points_per_centroid = int(kwargs.get("min_points_per_centroid", 5))
        self.train_max_points_per_centroid = int(kwargs.get("max_points_per_centroid", 256))
        self.seed = int(kwargs.get("seed", 12345))

        self._pending = []
        self._pending_ntotal = 0

        self.index = None
        self._ntotal = 0

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

    def _make_index(self, nlist: int):
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, int(nlist), faiss.METRIC_L2)
        try:
            index.parallel_mode = 3
        except Exception:
            pass

        try:
            cp = index.cp
            cp.niter = int(self.train_niter)
            cp.nredo = int(self.train_nredo)
            cp.verbose = False
            cp.min_points_per_centroid = int(self.train_min_points_per_centroid)
            cp.max_points_per_centroid = int(self.train_max_points_per_centroid)
            cp.seed = int(self.seed)
        except Exception:
            pass

        index.nprobe = int(self.nprobe)
        return index

    def _choose_train_size(self, total: int, nlist: int) -> int:
        if total <= 0:
            return 0
        if self.train_size is not None:
            ntrain = int(self.train_size)
        else:
            ntrain = max(200000, nlist * 15)
        ntrain = min(total, ntrain)
        ntrain = max(min(total, nlist), ntrain)
        return int(ntrain)

    def _ensure_trained_and_add_pending(self):
        if faiss is None:
            return

        if self.index is None:
            total = self._pending_ntotal
            if total <= 0:
                self.index = self._make_index(max(1, min(self.nlist, 1)))
                return

            nlist_eff = int(self.nlist)
            if total < nlist_eff:
                nlist_eff = max(1, total)
            self.index = self._make_index(nlist_eff)

        if not self.index.is_trained:
            total = self._pending_ntotal
            if total <= 0:
                return

            nlist_eff = int(self.index.nlist)
            ntrain = self._choose_train_size(total, nlist_eff)

            rng = np.random.default_rng(self.seed)
            if len(self._pending) == 1:
                xb_all = self._pending[0]
            else:
                xb_all = np.vstack(self._pending)

            if ntrain < xb_all.shape[0]:
                idx = rng.choice(xb_all.shape[0], size=ntrain, replace=False)
                xt = xb_all[idx]
            else:
                xt = xb_all

            xt = np.ascontiguousarray(xt, dtype=np.float32)
            self.index.train(xt)

        if self._pending_ntotal > 0:
            if len(self._pending) == 1:
                xb_all = self._pending[0]
            else:
                xb_all = np.vstack(self._pending)
            xb_all = np.ascontiguousarray(xb_all, dtype=np.float32)
            self.index.add(xb_all)
            self._ntotal += xb_all.shape[0]
            self._pending.clear()
            self._pending_ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is None:
            if not hasattr(self, "xb"):
                self.xb = xb.copy()
            else:
                self.xb = np.vstack([self.xb, xb])
            self._ntotal = int(self.xb.shape[0])
            return

        if self.index is not None and self.index.is_trained and self._pending_ntotal == 0:
            self.index.add(xb)
            self._ntotal += xb.shape[0]
            return

        self._pending.append(xb)
        self._pending_ntotal += xb.shape[0]

        if self._pending_ntotal >= max(100000, min(400000, self._pending_ntotal)):
            self._ensure_trained_and_add_pending()

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        nq = xq.shape[0]
        if nq == 0:
            return (np.empty((0, k), dtype=np.float32), np.empty((0, k), dtype=np.int64))

        if faiss is None:
            if not hasattr(self, "xb") or self.xb is None or self.xb.shape[0] == 0:
                return (np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64))
            xb = self.xb
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1)[None, :]
            dots = xq @ xb.T
            D = xq_norm + xb_norm - 2.0 * dots
            idx = np.argpartition(D, k - 1, axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dsel = D[row, idx]
            order = np.argsort(dsel, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            Dk = dsel[row, order].astype(np.float32, copy=False)
            return Dk, I

        self._ensure_trained_and_add_pending()

        if self.index is None or self._ntotal == 0:
            return (np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64))

        self.index.nprobe = int(self.nprobe)
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I


__all__ = ["YourIndexClass"]