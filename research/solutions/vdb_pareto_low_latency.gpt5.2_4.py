import numpy as np
from typing import Tuple, Optional

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 48))
        self.train_size = int(kwargs.get("train_size", 250_000))
        self.kmeans_niter = int(kwargs.get("kmeans_niter", 20))
        self.kmeans_nredo = int(kwargs.get("kmeans_nredo", 1))
        self.seed = int(kwargs.get("seed", 12345))

        self.use_hnsw_quantizer = bool(kwargs.get("use_hnsw_quantizer", True))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_construction = int(kwargs.get("hnsw_ef_construction", 80))
        self.hnsw_ef_search = kwargs.get("hnsw_ef_search", None)

        self._count = 0
        self._train_buf: Optional[np.ndarray] = None
        self._index = None

        if faiss is None:  # pragma: no cover
            self._xb = None
            return

        nt = kwargs.get("threads", None)
        if nt is not None:
            try:
                faiss.omp_set_num_threads(int(nt))
            except Exception:
                pass

        if self.use_hnsw_quantizer:
            quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
            quantizer.hnsw.efConstruction = self.hnsw_ef_construction
            if self.hnsw_ef_search is None:
                self.hnsw_ef_search = max(64, self.nprobe * 8)
            quantizer.hnsw.efSearch = int(self.hnsw_ef_search)
        else:
            quantizer = faiss.IndexFlatL2(self.dim)

        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        try:
            index.cp.niter = self.kmeans_niter
            index.cp.nredo = self.kmeans_nredo
            index.cp.seed = self.seed
            index.cp.max_points_per_centroid = 256
            index.cp.min_points_per_centroid = 5
        except Exception:
            pass

        index.nprobe = self.nprobe
        self._index = index

    def _ensure_float32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _maybe_train(self, xb: np.ndarray) -> None:
        if faiss is None:  # pragma: no cover
            return
        if self._index is None:
            return
        if self._index.is_trained:
            return

        n = xb.shape[0]
        if n <= 0:
            return

        if self._train_buf is None:
            need = min(self.train_size, n)
            if need == n:
                train_x = xb
            else:
                step = max(1, n // need)
                idx = np.arange(0, step * need, step, dtype=np.int64)
                train_x = xb[idx]
            self._train_buf = train_x.copy() if train_x is xb else train_x
        else:
            if self._train_buf.shape[0] < self.train_size:
                remaining = self.train_size - self._train_buf.shape[0]
                take = min(remaining, n)
                if take > 0:
                    step = max(1, n // take)
                    idx = np.arange(0, step * take, step, dtype=np.int64)
                    add_x = xb[idx]
                    self._train_buf = np.vstack([self._train_buf, add_x])

        if self._train_buf is not None and self._train_buf.shape[0] >= min(self.train_size, self.nlist * 10):
            self._index.train(self._train_buf)
            self._train_buf = None

    def add(self, xb: np.ndarray) -> None:
        xb = self._ensure_float32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is None:  # pragma: no cover
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            self._count += xb.shape[0]
            return

        self._maybe_train(xb)
        if self._index is None:
            raise RuntimeError("FAISS index not initialized")

        if not self._index.is_trained:
            n = xb.shape[0]
            if n >= min(self.train_size, self.nlist * 10):
                need = min(self.train_size, n)
                if need == n:
                    train_x = xb
                else:
                    step = max(1, n // need)
                    idx = np.arange(0, step * need, step, dtype=np.int64)
                    train_x = xb[idx]
                self._index.train(train_x)
            else:
                if self._train_buf is None:
                    self._train_buf = xb.copy()
                else:
                    self._train_buf = np.vstack([self._train_buf, xb])
                if self._train_buf.shape[0] >= min(self.train_size, self.nlist * 10):
                    self._index.train(self._train_buf)
                    self._train_buf = None

        if not self._index.is_trained:
            return

        self._index.add(xb)
        self._count += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = self._ensure_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        nq = xq.shape[0]

        if faiss is None:  # pragma: no cover
            if self._xb is None or self._xb.shape[0] == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._xb
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
            D2 = xq_norm + xb_norm - 2.0 * (xq @ xb.T)
            I = np.argpartition(D2, kth=min(k - 1, D2.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            Di = D2[row, I]
            o = np.argsort(Di, axis=1)
            I = I[row, o].astype(np.int64, copy=False)
            D = Di[row, o].astype(np.float32, copy=False)
            return D, I

        if self._index is None or (not self._index.is_trained):
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        if self._index.nprobe != self.nprobe:
            self._index.nprobe = self.nprobe
        if self.use_hnsw_quantizer:
            try:
                q = self._index.quantizer
                if hasattr(q, "hnsw") and q.hnsw.efSearch < max(64, self.nprobe * 4):
                    q.hnsw.efSearch = max(64, self.nprobe * 8)
            except Exception:
                pass

        D, I = self._index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I