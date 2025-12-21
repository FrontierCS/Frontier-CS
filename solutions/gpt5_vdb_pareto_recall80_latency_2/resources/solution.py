import os
from typing import Tuple
import numpy as np

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 5))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_search = int(kwargs.get("hnsw_ef_search", 128))
        self.train_samples = int(kwargs.get("train_samples", 100000))
        self.random_seed = int(kwargs.get("random_seed", 123))
        self._xb = None
        self._index = None
        self._trained = False

        if faiss is not None:
            try:
                nthreads_env = os.environ.get("FAISS_NTHREADS")
                if nthreads_env is not None:
                    nthreads = max(1, int(nthreads_env))
                else:
                    nthreads = max(1, min(8, os.cpu_count() or 8))
                faiss.omp_set_num_threads(nthreads)
            except Exception:
                pass

    def _build_index(self):
        if faiss is None:
            raise RuntimeError("faiss is required for this index.")
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
        quantizer.hnsw.efSearch = self.hnsw_ef_search
        quantizer.hnsw.efConstruction = max(self.hnsw_m * 2, 40)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        index.nprobe = self.nprobe
        self._index = index

    def _maybe_train(self, xb: np.ndarray):
        if self._trained:
            return
        if self._index is None:
            self._build_index()

        rs = np.random.RandomState(self.random_seed)
        n = xb.shape[0]
        nsamp = min(self.train_samples, n)
        if nsamp == n:
            xtrain = xb
        else:
            idx = rs.choice(n, nsamp, replace=False)
            xtrain = xb[idx]
        if not self._index.is_trained:
            self._index.train(xtrain)
        self._trained = True

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dtype float32")

        if self._xb is None:
            self._xb = xb.copy()
        else:
            self._xb = np.vstack((self._xb, xb))

        self._maybe_train(xb)
        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dtype float32")
        if self._index is None or not self._trained:
            raise RuntimeError("Index not built/trained. Call add() first.")
        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        D, I = self._index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
