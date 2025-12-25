import os
import numpy as np
from typing import Tuple

import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.threads = int(kwargs.get("threads", min(8, os.cpu_count() or 1)))
        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 512))

        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.quantizer_ef_search = int(kwargs.get("quantizer_ef_search", 512))
        self.quantizer_ef_construction = int(kwargs.get("quantizer_ef_construction", 200))

        self.train_size = int(kwargs.get("train_size", 100000))
        self.clustering_niter = int(kwargs.get("clustering_niter", 15))
        self.seed = int(kwargs.get("seed", 12345))

        self.quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m, faiss.METRIC_L2)
        self.quantizer.hnsw.efSearch = self.quantizer_ef_search
        self.quantizer.hnsw.efConstruction = self.quantizer_ef_construction

        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        try:
            self.index.cp.niter = self.clustering_niter
            self.index.cp.seed = self.seed
            self.index.cp.verbose = False
        except Exception:
            pass

        self.index.nprobe = min(self.nprobe, self.nlist)
        self._trained = False
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
            ts = min(self.train_size, n)
            if ts <= 0:
                raise ValueError("Cannot train on empty xb")
            if ts == n:
                train_x = xb
            else:
                rng = np.random.default_rng(self.seed)
                idx = rng.choice(n, size=ts, replace=False)
                train_x = xb[idx]
            self.index.train(train_x)
            self._trained = True
            self.index.nprobe = min(self.nprobe, self.nlist)

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

        nq = xq.shape[0]
        if self._ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        self.index.nprobe = min(self.nprobe, self.nlist)

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I