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

        self.n_threads = int(kwargs.get("n_threads", min(8, os.cpu_count() or 1)))

        self.nlist = int(kwargs.get("nlist", 8192))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))

        self.nprobe = int(kwargs.get("nprobe", 320))
        self.k_factor = int(kwargs.get("k_factor", 200))

        self.train_size = int(kwargs.get("train_size", 200_000))
        self.min_train_size = int(kwargs.get("min_train_size", min(50_000, self.train_size)))

        self._pending: List[np.ndarray] = []
        self._pending_rows = 0

        self._index = None
        self._ntotal = 0

        if faiss is None:
            self._xb = None
            return

        faiss.omp_set_num_threads(self.n_threads)

        quantizer = faiss.IndexFlatL2(self.dim)
        base = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)

        if hasattr(base, "use_precomputed_table"):
            try:
                base.use_precomputed_table = 1
            except Exception:
                pass

        try:
            base.nprobe = self.nprobe
        except Exception:
            pass

        idx = faiss.IndexRefineFlat(base)
        try:
            idx.k_factor = self.k_factor
        except Exception:
            pass

        self._index = idx

    def _ensure_faiss_ready(self):
        if self._index is None:
            raise RuntimeError("FAISS is not available in this environment.")

    def _as_float32_contig(self, x: np.ndarray) -> np.ndarray:
        if x is None:
            raise ValueError("Input is None")
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _maybe_train_and_flush_pending(self):
        self._ensure_faiss_ready()
        if self._index.is_trained:
            if self._pending:
                for a in self._pending:
                    self._index.add(a)
                    self._ntotal += a.shape[0]
                self._pending.clear()
                self._pending_rows = 0
            return

        if self._pending_rows < self.min_train_size:
            return

        if len(self._pending) == 1:
            all_data = self._pending[0]
        else:
            all_data = np.vstack(self._pending)

        n = all_data.shape[0]
        if n <= self.train_size:
            train_x = all_data
        else:
            rng = np.random.RandomState(12345)
            idx = rng.choice(n, size=self.train_size, replace=False)
            train_x = all_data[idx]

        train_x = self._as_float32_contig(train_x)

        self._index.train(train_x)

        for a in self._pending:
            self._index.add(a)
            self._ntotal += a.shape[0]
        self._pending.clear()
        self._pending_rows = 0

    def add(self, xb: np.ndarray) -> None:
        if faiss is None:
            xb = self._as_float32_contig(xb)
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            return

        self._ensure_faiss_ready()
        xb = self._as_float32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if not self._index.is_trained:
            self._pending.append(xb)
            self._pending_rows += xb.shape[0]
            self._maybe_train_and_flush_pending()
            return

        self._index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        xq = self._as_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if faiss is None:
            if self._xb is None or self._xb.shape[0] == 0:
                nq = xq.shape[0]
                return (
                    np.full((nq, k), np.inf, dtype=np.float32),
                    np.full((nq, k), -1, dtype=np.int64),
                )
            xb = self._xb
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1)[None, :]
            dots = xq @ xb.T
            d2 = xq_norm + xb_norm - 2.0 * dots
            if k == 1:
                I = np.argmin(d2, axis=1).astype(np.int64)[:, None]
                D = d2[np.arange(d2.shape[0]), I[:, 0]].astype(np.float32)[:, None]
                return D, I
            idx = np.argpartition(d2, kth=k - 1, axis=1)[:, :k]
            part = d2[np.arange(d2.shape[0])[:, None], idx]
            order = np.argsort(part, axis=1)
            I = idx[np.arange(idx.shape[0])[:, None], order].astype(np.int64)
            D = d2[np.arange(d2.shape[0])[:, None], I].astype(np.float32)
            return D, I

        self._ensure_faiss_ready()
        self._maybe_train_and_flush_pending()

        if self._ntotal == 0:
            nq = xq.shape[0]
            return (
                np.full((nq, k), np.inf, dtype=np.float32),
                np.full((nq, k), -1, dtype=np.int64),
            )

        D, I = self._index.search(xq, k)

        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)

        return D, I