import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
    _FAISS_AVAILABLE = True
except Exception:
    faiss = None
    _FAISS_AVAILABLE = False


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.threads = int(kwargs.get("threads", 0) or 0)
        if self.threads <= 0:
            self.threads = 8

        self.nlist = int(kwargs.get("nlist", 2048))
        if self.nlist < 1:
            self.nlist = 1

        self.nprobe = int(kwargs.get("nprobe", 48))
        self.nprobe = max(1, min(self.nprobe, self.nlist))

        self.train_niter = int(kwargs.get("train_niter", 10))
        self.train_niter = max(1, self.train_niter)

        self.max_points_per_centroid = int(kwargs.get("max_points_per_centroid", 60))
        self.max_points_per_centroid = max(10, self.max_points_per_centroid)

        self.min_points_per_centroid = int(kwargs.get("min_points_per_centroid", 5))
        self.min_points_per_centroid = max(1, self.min_points_per_centroid)

        self.seed = int(kwargs.get("seed", 12345))

        self._xb_fallback = None
        self._pending = []
        self._pending_ntotal = 0

        self._index = None
        self._trained = False

        if _FAISS_AVAILABLE:
            try:
                faiss.omp_set_num_threads(self.threads)
            except Exception:
                pass

            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            try:
                index.cp.niter = self.train_niter
                index.cp.max_points_per_centroid = self.max_points_per_centroid
                index.cp.min_points_per_centroid = self.min_points_per_centroid
            except Exception:
                pass

            try:
                index.parallel_mode = 1
            except Exception:
                pass

            index.nprobe = self.nprobe
            self._index = index

    def _maybe_train_and_flush(self) -> None:
        if not _FAISS_AVAILABLE or self._index is None or self._trained:
            return
        if self._pending_ntotal <= 0:
            return

        xb_all = np.ascontiguousarray(np.vstack(self._pending), dtype=np.float32)
        n = xb_all.shape[0]

        desired_train = int(self.nlist * self.max_points_per_centroid)
        ntrain = min(n, max(desired_train, self.nlist * 20, 50000))
        if ntrain < self.nlist * self.min_points_per_centroid:
            return

        if ntrain < n:
            rng = np.random.default_rng(self.seed)
            idx = rng.choice(n, size=ntrain, replace=False)
            xt = xb_all[idx]
        else:
            xt = xb_all

        self._index.train(xt)
        self._trained = True
        self._index.add(xb_all)
        self._pending.clear()
        self._pending_ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if not _FAISS_AVAILABLE or self._index is None:
            if self._xb_fallback is None:
                self._xb_fallback = xb.copy()
            else:
                self._xb_fallback = np.vstack((self._xb_fallback, xb))
            return

        if self._trained:
            self._index.add(xb)
            return

        self._pending.append(xb)
        self._pending_ntotal += xb.shape[0]
        self._maybe_train_and_flush()

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if not _FAISS_AVAILABLE or self._index is None:
            xb = self._xb_fallback
            if xb is None or xb.shape[0] == 0:
                nq = xq.shape[0]
                return (
                    np.full((nq, k), np.inf, dtype=np.float32),
                    np.full((nq, k), -1, dtype=np.int64),
                )
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1)[None, :]
            dists = xq_norm + xb_norm - 2.0 * (xq @ xb.T)
            idx = np.argpartition(dists, kth=min(k - 1, dists.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(xq.shape[0])[:, None]
            dd = dists[row, idx]
            order = np.argsort(dd, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dd[row, order].astype(np.float32, copy=False)
            return D, I

        if not self._trained:
            self._maybe_train_and_flush()
            if not self._trained:
                nq = xq.shape[0]
                return (
                    np.full((nq, k), np.inf, dtype=np.float32),
                    np.full((nq, k), -1, dtype=np.int64),
                )

        nprobe = self.nprobe
        if k > 1:
            nprobe = min(self.nlist, max(nprobe, int(nprobe * (1.0 + 0.2 * np.log2(k)))))
        self._index.nprobe = nprobe

        D, I = self._index.search(xq, k)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        return D, I