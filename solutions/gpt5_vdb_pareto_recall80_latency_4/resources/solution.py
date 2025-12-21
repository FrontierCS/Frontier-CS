import numpy as np
from typing import Tuple

import faiss
import os


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 4))
        self.hnsw_M = int(kwargs.get("hnsw_M", 32))
        self.hnsw_efSearch = int(kwargs.get("efSearch", max(64, self.nprobe * 8)))
        self.hnsw_efConstruction = int(kwargs.get("efConstruction", 200))
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.refine_factor = int(kwargs.get("refine_factor", 32))
        self.train_size = int(kwargs.get("train_size", 100000))
        self.random_state = int(kwargs.get("random_state", 12345))
        n_threads = int(kwargs.get("n_threads", 0)) or int(os.environ.get("FAISS_NTHREADS", "0") or 0)
        if n_threads <= 0:
            try:
                n_threads = os.cpu_count() or 8
            except Exception:
                n_threads = 8
        try:
            faiss.omp_set_num_threads(int(n_threads))
        except Exception:
            pass
        self.index = None
        self.ntotal = 0

    def _build_index(self):
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_M)
        quantizer.hnsw.efConstruction = self.hnsw_efConstruction
        quantizer.hnsw.efSearch = self.hnsw_efSearch
        try:
            base = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)
        except TypeError:
            base = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
        try:
            base.by_residual = True
        except Exception:
            pass
        try:
            base.use_precomputed_table = 1
        except Exception:
            pass
        try:
            base.cp.niter = 15
        except Exception:
            pass
        try:
            base.quantizer_trains_alone = 2
        except Exception:
            pass
        base.nprobe = self.nprobe
        idx = base
        if self.use_opq:
            opq = faiss.OPQMatrix(self.dim, self.m)
            opq.niter = 25
            opq.verbose = False
            idx = faiss.IndexPreTransform(opq, base)
        if self.refine_factor and self.refine_factor > 1:
            try:
                idx = faiss.IndexRefineFlat(idx, self.refine_factor)
            except TypeError:
                idx = faiss.IndexRefineFlat(idx)
                for attr in ("kfactor", "k_factor", "kfac"):
                    if hasattr(idx, attr):
                        setattr(idx, attr, self.refine_factor)
                        break
        self.index = idx

    def _unwrap_to_ivf(self, idx):
        cur = idx
        visited = set()
        while True:
            nxt = None
            for attr in ("base_index", "index", "inner_index", "child", "shard"):
                if hasattr(cur, attr):
                    nxt = getattr(cur, attr)
                    break
            if nxt is None or nxt is cur or id(nxt) in visited:
                break
            visited.add(id(nxt))
            cur = nxt
        try:
            cur = faiss.downcast_index(cur)
        except Exception:
            pass
        return cur

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if self.index is None:
            self._build_index()
            n_train = min(self.train_size, xb.shape[0])
            rs = np.random.RandomState(self.random_state)
            if xb.shape[0] > n_train:
                idxs = rs.choice(xb.shape[0], size=n_train, replace=False)
                xtrain = xb[idxs]
            else:
                xtrain = xb
            self.index.train(xtrain)
            try:
                ivf = self._unwrap_to_ivf(self.index)
                if hasattr(ivf, "quantizer") and hasattr(ivf.quantizer, "hnsw"):
                    ivf.quantizer.hnsw.efSearch = self.hnsw_efSearch
            except Exception:
                pass
        self.index.add(xb)
        self.ntotal += xb.shape[0]
        try:
            ivf = self._unwrap_to_ivf(self.index)
            if hasattr(ivf, "nprobe"):
                ivf.nprobe = self.nprobe
        except Exception:
            pass

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if self.index is None or self.ntotal == 0:
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), -np.ones((nq, k), dtype=np.int64)
        try:
            ivf = self._unwrap_to_ivf(self.index)
            if hasattr(ivf, "nprobe"):
                ivf.nprobe = self.nprobe
            if hasattr(ivf, "quantizer") and hasattr(ivf.quantizer, "hnsw"):
                ivf.quantizer.hnsw.efSearch = self.hnsw_efSearch
        except Exception:
            pass
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32)
        if I.dtype != np.int64:
            I = I.astype(np.int64)
        return D, I
