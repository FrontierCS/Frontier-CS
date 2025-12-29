import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 8))

        self.n_threads = int(kwargs.get("n_threads", 8))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.quantizer_ef_search = int(kwargs.get("quantizer_ef_search", 64))

        self.train_size = int(kwargs.get("train_size", 262144))
        self.min_train_size = int(kwargs.get("min_train_size", max(50000, self.nlist * 20)))

        self._trained = False
        self._ntotal_added = 0

        self._pending = []
        self._index = None

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass
            self._index = self._create_faiss_index()

    def _create_faiss_index(self):
        try:
            quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
        except Exception:
            quantizer = faiss.IndexFlatL2(self.dim)

        try:
            if hasattr(quantizer, "hnsw"):
                quantizer.hnsw.efSearch = self.quantizer_ef_search
        except Exception:
            pass

        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        # Ensure exact assignments during clustering even if quantizer is approximate
        try:
            index.clustering_index = faiss.IndexFlatL2(self.dim)
        except Exception:
            pass

        try:
            index.cp.niter = int(os.environ.get("FAISS_KMEANS_NITER", "20"))
        except Exception:
            pass
        try:
            index.cp.max_points_per_centroid = 256
        except Exception:
            pass
        try:
            index.cp.min_points_per_centroid = 5
        except Exception:
            pass

        try:
            index.nprobe = self.nprobe
        except Exception:
            pass

        return index

    def _ensure_float32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32 or not x.flags["C_CONTIGUOUS"]:
            return np.ascontiguousarray(x, dtype=np.float32)
        return x

    def _sample_training(self, xb: np.ndarray, train_size: int) -> np.ndarray:
        n = xb.shape[0]
        if n <= train_size:
            return np.ascontiguousarray(xb, dtype=np.float32)
        step = max(1, n // train_size)
        xt = xb[::step][:train_size]
        return np.ascontiguousarray(xt, dtype=np.float32)

    def _maybe_train_and_flush(self):
        if self._trained or faiss is None or self._index is None:
            return

        if not self._pending:
            return

        total = sum(b.shape[0] for b in self._pending)
        if total < self.min_train_size:
            return

        # Build training set from pending batches (uniform stride over concatenation)
        # To avoid concatenating huge arrays, take proportional samples per batch.
        ts = min(self.train_size, total)
        xt_parts = []
        remaining = ts
        for b in self._pending:
            if remaining <= 0:
                break
            bn = b.shape[0]
            take = max(1, int(round(ts * (bn / total))))
            take = min(take, remaining, bn)
            xt_parts.append(self._sample_training(b, take))
            remaining -= take

        if not xt_parts:
            xt = self._sample_training(self._pending[0], min(self.train_size, self._pending[0].shape[0]))
        else:
            xt = np.ascontiguousarray(np.vstack(xt_parts), dtype=np.float32)
            if xt.shape[0] > ts:
                xt = xt[:ts].copy()

        self._index.train(xt)
        self._trained = True

        for b in self._pending:
            self._index.add(b)
            self._ntotal_added += b.shape[0]
        self._pending.clear()

    def add(self, xb: np.ndarray) -> None:
        xb = self._ensure_float32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is None or self._index is None:
            # Fallback (slow) storage
            if not hasattr(self, "_xb_store") or self._xb_store is None:
                self._xb_store = xb.copy()
            else:
                self._xb_store = np.vstack([self._xb_store, xb])
            self._ntotal_added = int(self._xb_store.shape[0])
            return

        if not self._trained:
            if xb.shape[0] >= self.min_train_size:
                ts = min(self.train_size, xb.shape[0])
                xt = self._sample_training(xb, ts)
                self._index.train(xt)
                self._trained = True
                self._index.add(xb)
                self._ntotal_added += xb.shape[0]
            else:
                self._pending.append(xb.copy())
                self._maybe_train_and_flush()
        else:
            self._index.add(xb)
            self._ntotal_added += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            nq = int(xq.shape[0])
            return (
                np.empty((nq, 0), dtype=np.float32),
                np.empty((nq, 0), dtype=np.int64),
            )

        xq = self._ensure_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if faiss is None or self._index is None:
            xb = getattr(self, "_xb_store", None)
            if xb is None or xb.shape[0] == 0:
                nq = int(xq.shape[0])
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._ensure_float32_contig(xb)
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
            dist = xq_norm + xb_norm - 2.0 * (xq @ xb.T)
            I = np.argpartition(dist, kth=min(k - 1, dist.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(dist.shape[0])[:, None]
            Dsel = dist[row, I]
            order = np.argsort(Dsel, axis=1)
            I = I[row, order].astype(np.int64, copy=False)
            D = Dsel[row, order].astype(np.float32, copy=False)
            return D, I

        self._maybe_train_and_flush()
        if not self._trained:
            nq = int(xq.shape[0])
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        try:
            faiss.omp_set_num_threads(self.n_threads)
        except Exception:
            pass

        try:
            self._index.nprobe = self.nprobe
        except Exception:
            pass
        try:
            q = getattr(self._index, "quantizer", None)
            if q is not None and hasattr(q, "hnsw"):
                q.hnsw.efSearch = self.quantizer_ef_search
        except Exception:
            pass

        D, I = self._index.search(xq, int(k))
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I