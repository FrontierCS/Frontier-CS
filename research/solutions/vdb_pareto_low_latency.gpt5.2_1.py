import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.m = int(kwargs.get("m", 32))
        self.nbits = int(kwargs.get("nbits", 8))

        self.nprobe = int(kwargs.get("nprobe", 64))
        self.k_factor = int(kwargs.get("k_factor", 128))
        self.max_candidates = int(kwargs.get("max_candidates", 4096))

        self.train_size = int(kwargs.get("train_size", 200000))
        self.seed = int(kwargs.get("seed", 123))

        self.use_hnsw_quantizer = bool(kwargs.get("use_hnsw_quantizer", False))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_search = int(kwargs.get("hnsw_ef_search", 64))

        self.num_threads = int(kwargs.get("num_threads", min(8, (os.cpu_count() or 1))))

        self._rng = np.random.RandomState(self.seed)

        self.base = None
        self.index = None
        self._ntotal = 0

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.num_threads)
            except Exception:
                pass

    def _create(self) -> None:
        if self.index is not None:
            return
        if faiss is None:
            raise RuntimeError("faiss is required in the evaluation environment")

        if self.use_hnsw_quantizer:
            quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
            try:
                quantizer.hnsw.efSearch = self.hnsw_ef_search
            except Exception:
                pass
        else:
            quantizer = faiss.IndexFlatL2(self.dim)

        try:
            base = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)
        except TypeError:
            base = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)

        try:
            base.nprobe = self.nprobe
        except Exception:
            pass

        try:
            base.cp.niter = int(os.environ.get("FAISS_CP_NITER", "20"))
        except Exception:
            pass
        try:
            base.cp.nredo = int(os.environ.get("FAISS_CP_NREDO", "1"))
        except Exception:
            pass

        if hasattr(faiss, "IndexRefineFlat"):
            idx = faiss.IndexRefineFlat(base)
        else:
            idx = base

        self.base = base
        self.index = idx

    def add(self, xb: np.ndarray) -> None:
        self._create()
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        n = int(xb.shape[0])
        if n == 0:
            return

        if hasattr(self.index, "is_trained") and not self.index.is_trained:
            min_train = max(self.nlist * 40, self.nlist, 10000)
            ts = min(n, max(min_train, min(self.train_size, n)))
            if ts < n:
                idx = self._rng.choice(n, size=ts, replace=False)
                xt = xb[idx]
            else:
                xt = xb
            self.base.train(xt)
            try:
                if hasattr(self.base, "use_precomputed_table"):
                    self.base.use_precomputed_table = 1
                if hasattr(self.base, "precompute_table"):
                    self.base.precompute_table()
            except Exception:
                pass

        self.index.add(xb)
        self._ntotal += n

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or self._ntotal == 0:
            nq = int(xq.shape[0])
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        k = int(k)
        if k <= 0:
            nq = int(xq.shape[0])
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        try:
            self.base.nprobe = self.nprobe
        except Exception:
            pass

        if hasattr(self.index, "k_factor"):
            eff = self.k_factor
            if self.max_candidates > 0:
                eff = min(eff, max(1, self.max_candidates // max(1, k)))
            eff = max(1, int(eff))
            try:
                self.index.k_factor = eff
            except Exception:
                pass

        D, I = self.index.search(xq, k)

        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)

        if np.any(I < 0):
            bad = I < 0
            if np.any(bad):
                I = I.copy()
                D = D.copy()
                I[bad] = 0
                D[bad] = np.inf

        return D, I