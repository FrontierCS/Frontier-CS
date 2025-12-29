import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    import faiss_cpu as faiss  # type: ignore


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 32))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))

        self.train_size = int(kwargs.get("train_size", 200000))
        self.ivf_niter = int(kwargs.get("ivf_niter", 20))
        self.pq_niter = int(kwargs.get("pq_niter", 25))
        self.opq_niter = int(kwargs.get("opq_niter", 25))
        self.use_opq = bool(kwargs.get("use_opq", True))

        self.threads = int(kwargs.get("threads", os.cpu_count() or 1))
        if self.threads < 1:
            self.threads = 1
        faiss.omp_set_num_threads(self.threads)

        quantizer = faiss.IndexFlatL2(self.dim)
        ivfpq = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)

        try:
            ivfpq.cp.niter = self.ivf_niter
        except Exception:
            pass

        try:
            ivfpq.pq.cp.niter = self.pq_niter
        except Exception:
            pass

        try:
            ivfpq.use_precomputed_tables = 1
        except Exception:
            pass

        ivfpq.nprobe = self.nprobe

        self._ivf = ivfpq
        self._opq = None
        self.index = None

        if self.use_opq:
            opq = faiss.OPQMatrix(self.dim, self.m)
            try:
                opq.niter = self.opq_niter
            except Exception:
                pass
            self._opq = opq
            self.index = faiss.IndexPreTransform(opq, ivfpq)
        else:
            self.index = ivfpq

        self._ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.asarray(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if not self.index.is_trained:
            n = xb.shape[0]
            ts = self.train_size
            if ts <= 0:
                ts = min(200000, n)
            ts = min(ts, n)

            if ts < self.nlist:
                ts = min(n, max(self.nlist, ts))

            xtrain = xb[:ts]
            self.index.train(xtrain)

            try:
                if self._ivf is not None:
                    self._ivf.precompute_table()
            except Exception:
                pass

        self.index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.asarray(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I