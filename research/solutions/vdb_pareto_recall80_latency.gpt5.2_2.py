import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as _e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 32))
        self.pq_m = int(kwargs.get("m", 32))
        self.pq_nbits = int(kwargs.get("nbits", 8))

        self.n_threads = int(kwargs.get("n_threads", min(8, os.cpu_count() or 1)))

        self.train_size = kwargs.get("train_size", None)
        self.clust_niter = int(kwargs.get("clust_niter", 10))
        self.max_points_per_centroid = int(kwargs.get("max_points_per_centroid", 256))
        self.use_precomputed_table = int(kwargs.get("use_precomputed_table", 1))

        self._index = None
        self._ntotal = 0

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

    def _ensure_index(self):
        if self._index is not None:
            return
        if faiss is None:
            raise RuntimeError("faiss is required but not available")

        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.pq_m, self.pq_nbits)

        try:
            index.nprobe = self.nprobe
        except Exception:
            pass

        try:
            index.parallel_mode = 1
        except Exception:
            pass

        try:
            cp = index.cp
            try:
                cp.niter = self.clust_niter
            except Exception:
                pass
            try:
                cp.max_points_per_centroid = self.max_points_per_centroid
            except Exception:
                pass
            try:
                cp.verbose = False
            except Exception:
                pass
        except Exception:
            pass

        if self.use_precomputed_table:
            try:
                index.use_precomputed_table = self.use_precomputed_table
            except Exception:
                pass

        self._index = index

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        self._ensure_index()

        if not self._index.is_trained:
            n = xb.shape[0]
            if self.train_size is None:
                min_needed = max(100000, int(self.nlist * 50))
                train_size = min(n, min_needed)
            else:
                train_size = min(n, int(self.train_size))

            if train_size < self.nlist:
                # Too small to train IVF properly; fall back to exact flat index
                flat = faiss.IndexFlatL2(self.dim)
                flat.add(xb)
                self._index = flat
                self._ntotal += n
                return

            step = max(1, n // train_size)
            xtrain = xb[::step][:train_size]
            xtrain = np.ascontiguousarray(xtrain, dtype=np.float32)

            self._index.train(xtrain)

        self._index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            raise ValueError("k must be >= 1")
        if self._index is None or self._ntotal == 0:
            raise RuntimeError("index is empty; call add() first")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

        try:
            self._index.nprobe = self.nprobe
        except Exception:
            pass

        D, I = self._index.search(xq, int(k))
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I