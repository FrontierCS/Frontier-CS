import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.M = int(kwargs.get("M", 64))
        self.ef_construction = int(kwargs.get("ef_construction", 400))
        self.ef_search = int(kwargs.get("ef_search", 1024))
        self.bounded_queue = bool(kwargs.get("bounded_queue", False))

        threads = kwargs.get("threads", None)
        if threads is None:
            threads = os.cpu_count() or 1
        self.threads = int(max(1, threads))

        if faiss is None:
            self._fallback_xb: Optional[np.ndarray] = None
            return

        faiss.omp_set_num_threads(self.threads)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        try:
            self.index.hnsw.search_bounded_queue = self.bounded_queue
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")
        if xb.size == 0:
            return
        xb = np.ascontiguousarray(xb)

        if faiss is None:
            if self._fallback_xb is None:
                self._fallback_xb = xb.copy()
            else:
                self._fallback_xb = np.vstack((self._fallback_xb, xb))
            return

        faiss.omp_set_num_threads(self.threads)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")
        xq = np.ascontiguousarray(xq)

        if faiss is None:
            if self._fallback_xb is None or self._fallback_xb.shape[0] == 0:
                nq = xq.shape[0]
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._fallback_xb
            nq = xq.shape[0]
            nb = xb.shape[0]
            kk = min(k, nb)
            xq2 = (xq * xq).sum(axis=1, keepdims=True)
            xb2 = (xb * xb).sum(axis=1)[None, :]
            scores = xq2 + xb2 - 2.0 * (xq @ xb.T)
            idx = np.argpartition(scores, kk - 1, axis=1)[:, :kk]
            row = np.arange(nq)[:, None]
            part = scores[row, idx]
            order = np.argsort(part, axis=1)
            Ikk = idx[row, order].astype(np.int64, copy=False)
            Dkk = part[row, order].astype(np.float32, copy=False)
            if kk < k:
                I = np.full((nq, k), -1, dtype=np.int64)
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I[:, :kk] = Ikk
                D[:, :kk] = Dkk
                return D, I
            return Dkk, Ikk

        faiss.omp_set_num_threads(self.threads)
        self.index.hnsw.efSearch = self.ef_search
        try:
            self.index.hnsw.search_bounded_queue = self.bounded_queue
        except Exception:
            pass
        D, I = self.index.search(xq, k)
        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)