import os
import numpy as np
from typing import Tuple

try:
    import faiss
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 8192))
        self.m = int(kwargs.get("m", 16))  # PQ subquantizers
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 6))
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.random_seed = int(kwargs.get("random_seed", 123))
        self.n_threads = int(kwargs.get("n_threads", os.cpu_count() or 8))
        self.metric = faiss.METRIC_L2 if faiss is not None else None

        self.index = None
        self.ntotal = 0
        self.trained = False
        self._rng = np.random.RandomState(self.random_seed)

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

    def _ensure_faiss_available(self):
        if faiss is None:
            raise RuntimeError("faiss is required but not available in the environment.")

    def _create_index(self):
        self._ensure_faiss_available()

        quantizer = faiss.IndexFlatL2(self.dim)
        ivfpq = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
        ivfpq.metric_type = faiss.METRIC_L2
        try:
            ivfpq.use_precomputed_table = 1
        except Exception:
            pass
        try:
            ivfpq.precomputed_table_type = 1  # auto
        except Exception:
            pass
        try:
            ivfpq.by_residual = True
        except Exception:
            pass

        if self.use_opq:
            opq = faiss.OPQMatrix(self.dim, self.m)
            self.index = faiss.IndexPreTransform(opq, ivfpq)
        else:
            self.index = ivfpq

    def _set_nprobe(self, nprobe: int):
        try:
            ivf = faiss.extract_index_ivf(self.index)
            ivf.nprobe = int(nprobe)
        except Exception:
            try:
                ps = faiss.ParameterSpace()
                ps.set_index_parameter(self.index, "nprobe", int(nprobe))
            except Exception:
                pass

    def _sample_training(self, xb: np.ndarray, size: int) -> np.ndarray:
        n = xb.shape[0]
        size = int(min(max(1024, size), n))
        if size == n:
            return xb
        idx = self._rng.choice(n, size=size, replace=False)
        return xb[idx].copy()

    def add(self, xb: np.ndarray) -> None:
        self._ensure_faiss_available()
        if not isinstance(xb, np.ndarray):
            xb = np.asarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dim=%d" % self.dim)

        if self.index is None:
            self._create_index()
            xtrain = self._sample_training(xb, self.train_size)
            self.index.train(xtrain)
            self.trained = True
            self._set_nprobe(self.nprobe)

        self.index.add(xb)
        self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self._ensure_faiss_available()
        if self.index is None or not self.trained or self.ntotal == 0:
            raise RuntimeError("Index is not trained or contains no vectors. Call add() first.")

        if not isinstance(xq, np.ndarray):
            xq = np.asarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dim=%d" % self.dim)

        self._set_nprobe(self.nprobe)

        D, I = self.index.search(xq, int(k))
        if D is None or I is None:
            # Fallback to empty results if FAISS returns None (shouldn't happen)
            nq = xq.shape[0]
            D = np.full((nq, k), np.float32(np.inf), dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
        else:
            if D.dtype != np.float32:
                D = D.astype(np.float32, copy=False)
            if I.dtype != np.int64:
                I = I.astype(np.int64, copy=False)

        return D, I