import os
from typing import Tuple, Optional, Any, Dict

import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 8))
        self.m = int(kwargs.get("m", 32))
        self.nbits = int(kwargs.get("nbits", 8))

        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_search = int(kwargs.get("hnsw_ef_search", 64))
        self.hnsw_ef_construction = int(kwargs.get("hnsw_ef_construction", 80))

        self.train_size = int(kwargs.get("train_size", 100000))
        self.add_chunk_size = int(kwargs.get("add_chunk_size", 200000))

        threads = kwargs.get("threads", None)
        self.threads = int(threads) if threads is not None else (os.cpu_count() or 8)

        self._index = None
        self._ntotal = 0

        if faiss is None:
            raise RuntimeError("faiss is required in the evaluation environment")

        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        if self.dim % self.m != 0:
            raise ValueError(f"dim ({self.dim}) must be divisible by m ({self.m}) for PQ")

        self._build_index()

    def _build_index(self) -> None:
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m, faiss.METRIC_L2)
        try:
            quantizer.hnsw.efSearch = self.hnsw_ef_search
            quantizer.hnsw.efConstruction = self.hnsw_ef_construction
        except Exception:
            pass

        index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)
        index.nprobe = self.nprobe

        try:
            index.use_precomputed_table = 1
        except Exception:
            pass

        try:
            index.set_direct_map_type(faiss.DirectMap.NoMap)
        except Exception:
            pass

        self._index = index

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        n = xb.shape[0]
        if n == 0:
            return

        if not self._index.is_trained:
            ntrain = min(self.train_size, n)
            if ntrain < max(1024, self.nlist):
                ntrain = n
            if ntrain < 1:
                raise ValueError("Not enough vectors to train")

            if ntrain == n:
                xtrain = xb
            else:
                rng = np.random.default_rng(12345)
                idx = rng.choice(n, size=ntrain, replace=False)
                xtrain = np.ascontiguousarray(xb[idx], dtype=np.float32)

            self._index.train(xtrain)

            try:
                self._index.precompute_table()
            except Exception:
                pass

        cs = self.add_chunk_size
        if cs <= 0:
            self._index.add(xb)
            self._ntotal += n
            return

        for i in range(0, n, cs):
            self._index.add(xb[i : i + cs])
        self._ntotal += n

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._index is None or self._ntotal == 0:
            nq = 0 if xq is None else int(xq.shape[0])
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if k <= 0:
            nq = xq.shape[0]
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        D, I = self._index.search(xq, int(k))
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I