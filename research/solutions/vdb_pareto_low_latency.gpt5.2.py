import os
import numpy as np
from typing import Tuple, Optional

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.num_threads = int(kwargs.get("num_threads", min(8, os.cpu_count() or 1)))

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 16))

        self.train_size = int(kwargs.get("train_size", 100000))
        self.clustering_niter = int(kwargs.get("clustering_niter", 12))

        self.use_hnsw_quantizer = bool(kwargs.get("use_hnsw_quantizer", True))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.quantizer_ef_search = int(kwargs.get("quantizer_ef_search", max(64, self.nprobe * 8)))
        self.quantizer_ef_construction = int(kwargs.get("quantizer_ef_construction", 200))

        self._index = None
        self._ntotal = 0
        self._pending = []
        self._pending_rows = 0

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.num_threads)
            except Exception:
                pass

    def _ensure_index(self) -> None:
        if self._index is not None:
            return
        if faiss is None:
            self._index = None
            return

        if self.use_hnsw_quantizer:
            quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m, faiss.METRIC_L2)
            try:
                quantizer.hnsw.efSearch = self.quantizer_ef_search
                quantizer.hnsw.efConstruction = self.quantizer_ef_construction
            except Exception:
                pass
        else:
            quantizer = faiss.IndexFlatL2(self.dim)

        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        try:
            index.cp.niter = self.clustering_niter
            index.cp.verbose = False
        except Exception:
            pass
        try:
            index.nprobe = self.nprobe
        except Exception:
            pass

        self._index = index

    @staticmethod
    def _as_float32_contig(x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        return np.ascontiguousarray(x)

    def _train_and_flush_pending(self, xb_for_train: Optional[np.ndarray] = None) -> None:
        if faiss is None:
            return
        self._ensure_index()
        if self._index is None:
            return
        if self._index.is_trained:
            if self._pending_rows:
                for a in self._pending:
                    self._index.add(a)
                    self._ntotal += a.shape[0]
                self._pending.clear()
                self._pending_rows = 0
            return

        if xb_for_train is not None and xb_for_train.shape[0] > 0:
            train_src = xb_for_train
        elif self._pending_rows:
            train_src = self._pending[0] if len(self._pending) == 1 else np.vstack(self._pending)
        else:
            return

        n = train_src.shape[0]
        if n > self.train_size:
            rng = np.random.default_rng(12345)
            idx = rng.choice(n, size=self.train_size, replace=False)
            xt = np.ascontiguousarray(train_src[idx])
        else:
            xt = train_src

        self._index.train(xt)

        if self._pending_rows:
            for a in self._pending:
                self._index.add(a)
                self._ntotal += a.shape[0]
            self._pending.clear()
            self._pending_rows = 0

        try:
            self._index.nprobe = self.nprobe
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_float32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is None:
            if not hasattr(self, "_xb_store"):
                self._xb_store = xb.copy()
            else:
                self._xb_store = np.vstack([self._xb_store, xb])
            self._ntotal = int(self._xb_store.shape[0])
            return

        self._ensure_index()
        if self._index is None:
            return

        if not self._index.is_trained:
            if self._pending_rows == 0 and xb.shape[0] >= min(self.train_size, 5000):
                self._train_and_flush_pending(xb_for_train=xb)
                self._index.add(xb)
                self._ntotal += xb.shape[0]
            else:
                self._pending.append(xb)
                self._pending_rows += xb.shape[0]
                if self._pending_rows >= self.train_size:
                    self._train_and_flush_pending()
        else:
            self._index.add(xb)
            self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = self._as_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        nq = xq.shape[0]
        if self._ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        if faiss is None:
            xb = self._xb_store
            x2 = (xq * xq).sum(axis=1, keepdims=True)
            b2 = (xb * xb).sum(axis=1, keepdims=True).T
            sims = x2 + b2 - 2.0 * (xq @ xb.T)
            idx = np.argpartition(sims, kth=min(k - 1, sims.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dsel = sims[row, idx]
            order = np.argsort(dsel, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dsel[row, order].astype(np.float32, copy=False)
            return D, I

        self._ensure_index()
        if self._index is None:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        if not self._index.is_trained or self._pending_rows:
            self._train_and_flush_pending()

        try:
            self._index.nprobe = self.nprobe
        except Exception:
            pass
        if self.use_hnsw_quantizer:
            try:
                self._index.quantizer.hnsw.efSearch = self.quantizer_ef_search
            except Exception:
                pass

        D, I = self._index.search(xq, k)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        return D, I