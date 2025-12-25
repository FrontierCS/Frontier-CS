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
        self.nprobe = int(kwargs.get("nprobe", 16))

        self.m = int(kwargs.get("m", 32))
        self.nbits = int(kwargs.get("nbits", 8))
        self.use_opq = bool(kwargs.get("use_opq", True))

        self.train_size = int(kwargs.get("train_size", 200000))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.quantizer_ef_search = int(kwargs.get("quantizer_ef_search", 64))

        self.n_threads = int(kwargs.get("n_threads", min(8, (os.cpu_count() or 1))))

        self._index = None
        self._ntotal = 0

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

    def _ensure_index(self):
        if self._index is not None or faiss is None:
            return

        d = self.dim
        nlist = self.nlist
        m = self.m
        nbits = self.nbits
        hnsw_m = self.hnsw_m

        if self.use_opq:
            descr = f"OPQ{m}_{d},IVF{nlist}_HNSW{hnsw_m},PQ{m}x{nbits}"
        else:
            descr = f"IVF{nlist}_HNSW{hnsw_m},PQ{m}x{nbits}"

        try:
            self._index = faiss.index_factory(d, descr, faiss.METRIC_L2)
        except Exception:
            # Fallback: flat quantizer
            if self.use_opq:
                descr = f"OPQ{m}_{d},IVF{nlist},PQ{m}x{nbits}"
            else:
                descr = f"IVF{nlist},PQ{m}x{nbits}"
            self._index = faiss.index_factory(d, descr, faiss.METRIC_L2)

        try:
            ivf = faiss.extract_index_ivf(self._index)
            if ivf is not None:
                ivf.nprobe = self.nprobe
        except Exception:
            pass

        try:
            # If the IVF quantizer is HNSW, set efSearch for centroid assignment
            ivf = faiss.extract_index_ivf(self._index)
            if ivf is not None and hasattr(ivf, "quantizer") and hasattr(ivf.quantizer, "hnsw"):
                ivf.quantizer.hnsw.efSearch = self.quantizer_ef_search
        except Exception:
            pass

    @staticmethod
    def _as_contig_f32(x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_contig_f32(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim)")

        if faiss is None:
            raise RuntimeError("faiss is required for this solution")

        self._ensure_index()
        idx = self._index

        if not idx.is_trained:
            n = xb.shape[0]
            ts = min(self.train_size, n)
            if ts < n:
                step = max(1, n // ts)
                xt = xb[::step][:ts]
            else:
                xt = xb
            xt = self._as_contig_f32(xt)
            idx.train(xt)

        idx.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if faiss is None:
            raise RuntimeError("faiss is required for this solution")

        if self._index is None or self._ntotal == 0:
            raise RuntimeError("Index is empty; call add() first")

        xq = self._as_contig_f32(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim)")

        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        try:
            ivf = faiss.extract_index_ivf(self._index)
            if ivf is not None:
                ivf.nprobe = self.nprobe
                if hasattr(ivf, "quantizer") and hasattr(ivf.quantizer, "hnsw"):
                    ivf.quantizer.hnsw.efSearch = self.quantizer_ef_search
        except Exception:
            pass

        D, I = self._index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I