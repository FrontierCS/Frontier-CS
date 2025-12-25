import numpy as np
from typing import Tuple, Optional

try:
    import faiss  # type: ignore
except Exception as _e:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", kwargs.get("ef_search", 64)))
        self.train_size = int(kwargs.get("train_size", max(100000, min(400000, self.nlist * 50))))
        self.niter = int(kwargs.get("niter", 15))
        self.n_threads = int(kwargs.get("n_threads", 8))

        self._index: Optional[object] = None
        self._pending = []
        self._pending_rows = 0
        self._use_faiss = faiss is not None

        if self._use_faiss:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass
            try:
                faiss.cvar.clustering_seed = int(kwargs.get("seed", 12345))
            except Exception:
                pass

    def _ensure_index(self, total_rows_hint: int = 0) -> None:
        if self._index is not None:
            return

        if not self._use_faiss:
            self._index = {"xb": None}
            return

        # If very small dataset, flat index is fastest and exact.
        if total_rows_hint > 0 and total_rows_hint < max(2048, self.nlist // 2):
            self._index = faiss.IndexFlatL2(self.dim)
            return

        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        try:
            index.cp.niter = self.niter
        except Exception:
            pass
        try:
            index.cp.max_points_per_centroid = 256
        except Exception:
            pass

        self._index = index

    def _train_if_needed(self) -> None:
        if not self._use_faiss or self._index is None:
            return

        index = self._index
        if isinstance(index, faiss.IndexFlat):
            return

        if index.is_trained:
            return

        if self._pending_rows <= 0:
            return

        xb_all = np.ascontiguousarray(np.vstack(self._pending), dtype=np.float32)
        n = xb_all.shape[0]

        # If too few points, fall back to exact.
        if n < max(self.nlist, 2048):
            flat = faiss.IndexFlatL2(self.dim)
            flat.add(xb_all)
            self._index = flat
            self._pending = []
            self._pending_rows = 0
            return

        ntrain = min(n, self.train_size)
        if ntrain < n:
            rng = np.random.default_rng(12345)
            sel = rng.choice(n, size=ntrain, replace=False)
            xt = xb_all[sel]
        else:
            xt = xb_all

        index.train(xt)
        index.add(xb_all)

        self._pending = []
        self._pending_rows = 0

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        self._ensure_index(total_rows_hint=int(xb.shape[0] + self._pending_rows))

        if not self._use_faiss:
            if self._index["xb"] is None:
                self._index["xb"] = xb.copy()
            else:
                self._index["xb"] = np.vstack([self._index["xb"], xb])
            return

        index = self._index
        if isinstance(index, faiss.IndexFlat):
            index.add(xb)
            return

        if not index.is_trained:
            self._pending.append(xb)
            self._pending_rows += int(xb.shape[0])
            if self._pending_rows >= max(self.nlist * 10, min(self.train_size, self.nlist * 50)):
                self._train_if_needed()
            return

        index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            raise ValueError("k must be >= 1")
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if self._index is None:
            self._ensure_index(total_rows_hint=0)

        if self._use_faiss:
            if not isinstance(self._index, faiss.IndexFlat) and not self._index.is_trained:
                self._train_if_needed()
            if not isinstance(self._index, faiss.IndexFlat):
                try:
                    self._index.nprobe = min(self.nprobe, self.nlist)
                except Exception:
                    pass

            D, I = self._index.search(xq, int(k))
            D = np.ascontiguousarray(D, dtype=np.float32)
            I = np.ascontiguousarray(I, dtype=np.int64)

            # Ensure exactly k outputs (Faiss should already do this, but be defensive)
            if D.shape[1] != k or I.shape[1] != k:
                D2 = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
                I2 = np.full((xq.shape[0], k), -1, dtype=np.int64)
                kk = min(k, D.shape[1])
                D2[:, :kk] = D[:, :kk]
                I2[:, :kk] = I[:, :kk]
                D, I = D2, I2

            if np.any(I < 0):
                bad = (I < 0)
                D[bad] = np.float32(np.inf)
                I[bad] = np.int64(0)

            return D, I

        # Fallback (slow): exact brute force in NumPy
        xb = self._index["xb"]
        if xb is None or xb.shape[0] == 0:
            D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
            I = np.zeros((xq.shape[0], k), dtype=np.int64)
            return D, I

        xq_norm = (xq * xq).sum(axis=1, keepdims=True)
        xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
        dist = xq_norm + xb_norm - 2.0 * (xq @ xb.T)
        if k == 1:
            idx = np.argmin(dist, axis=1).astype(np.int64)
            d = dist[np.arange(dist.shape[0]), idx].astype(np.float32)
            return d.reshape(-1, 1), idx.reshape(-1, 1)
        idx = np.argpartition(dist, kth=k - 1, axis=1)[:, :k].astype(np.int64)
        dsel = dist[np.arange(dist.shape[0])[:, None], idx]
        ord_ = np.argsort(dsel, axis=1)
        idx = idx[np.arange(idx.shape[0])[:, None], ord_]
        dsel = dsel[np.arange(dsel.shape[0])[:, None], ord_].astype(np.float32)
        return dsel, idx.astype(np.int64)