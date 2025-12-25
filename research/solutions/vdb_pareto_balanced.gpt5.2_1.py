import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 1024))
        self.k_factor = int(kwargs.get("k_factor", 256))

        self.seed = int(kwargs.get("seed", 123))
        self.niter = int(kwargs.get("niter", 20))

        default_train_size = max(200_000, 32 * self.nlist)
        self.train_size = int(kwargs.get("train_size", default_train_size))

        self.threads = int(kwargs.get("threads", min(8, (os.cpu_count() or 8))))
        self.use_refine = bool(kwargs.get("use_refine", True))

        self._index = None
        self._base = None
        self._trained = False

        if faiss is None:  # pragma: no cover
            self._xb = None
            return

        faiss.omp_set_num_threads(self.threads)

        quantizer = faiss.IndexFlatL2(self.dim)

        qtype = kwargs.get("qtype", None)
        if qtype is None:
            qtype = faiss.ScalarQuantizer.QT_8bit
        metric = faiss.METRIC_L2

        base = faiss.IndexIVFScalarQuantizer(quantizer, self.dim, self.nlist, qtype, metric)
        try:
            base.cp.seed = self.seed
            base.cp.niter = self.niter
            base.cp.max_points_per_centroid = int(kwargs.get("max_points_per_centroid", 256))
        except Exception:
            pass

        base.nprobe = min(self.nprobe, self.nlist)

        if self.use_refine:
            index = faiss.IndexRefineFlat(base)
            try:
                index.k_factor = max(1, self.k_factor)
            except Exception:
                pass
            self._index = index
        else:
            self._index = base

        self._base = base

    def _ensure_faiss_ready(self):
        if faiss is None:  # pragma: no cover
            raise RuntimeError("faiss is required but not available in this environment")

        if self._index is None or self._base is None:
            raise RuntimeError("Index not initialized")

    @staticmethod
    def _as_float32_contig(x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def add(self, xb: np.ndarray) -> None:
        if faiss is None:  # pragma: no cover
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
            n = xb.shape[0]
            ts = min(n, max(self.nlist, self.train_size))
            if ts == n:
                xtrain = xb
            else:
                rng = np.random.default_rng(self.seed)
                sel = rng.choice(n, size=ts, replace=False)
                xtrain = xb[sel]
                if not xtrain.flags["C_CONTIGUOUS"]:
                    xtrain = np.ascontiguousarray(xtrain)
            self._index.train(xtrain)

        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        if faiss is None:  # pragma: no cover
            xq = self._as_float32_contig(xq)
            if self._xb is None:
                nq = xq.shape[0]
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._xb
            nq = xq.shape[0]
            D = np.empty((nq, k), dtype=np.float32)
            I = np.empty((nq, k), dtype=np.int64)
            xb_norm = (xb * xb).sum(axis=1)
            for i in range(nq):
                q = xq[i]
                dists = xb_norm - 2.0 * xb.dot(q) + float((q * q).sum())
                idx = np.argpartition(dists, k - 1)[:k]
                ord2 = np.argsort(dists[idx])
                idx = idx[ord2]
                I[i] = idx.astype(np.int64, copy=False)
                D[i] = dists[idx].astype(np.float32, copy=False)
            return D, I

        self._ensure_faiss_ready()
        xq = self._as_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if xq.shape[0] == 0:
            return np.empty((0, k), dtype=np.float32), np.empty((0, k), dtype=np.int64)

        self._base.nprobe = min(self.nprobe, self.nlist)

        if self.use_refine:
            try:
                self._index.k_factor = max(1, max(self.k_factor, 4 * k))
            except Exception:
                pass

        D, I = self._index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I