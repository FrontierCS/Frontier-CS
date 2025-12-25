import os

os.environ.setdefault("OMP_NUM_THREADS", str(min(8, (os.cpu_count() or 1))))
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 8))

        self.use_opq = bool(kwargs.get("use_opq", True))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))

        self.k_factor = int(kwargs.get("k_factor", 128))

        self.train_size = int(kwargs.get("train_size", 200000))
        self.min_train = int(kwargs.get("min_train", max(50000, self.nlist * 20)))

        self.threads = int(kwargs.get("threads", min(8, (os.cpu_count() or 1))))

        self._index = None
        self._trained = False
        self._pending = []
        self._pending_count = 0

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.threads)
            except Exception:
                pass
            try:
                faiss.cvar.rand_seed = 1234
            except Exception:
                pass

    def _ensure_faiss(self):
        if faiss is None:
            raise RuntimeError("faiss is required but could not be imported")

    def _as_f32_c(self, x: np.ndarray) -> np.ndarray:
        if x is None:
            return x
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _train_sample(self, xb: np.ndarray) -> np.ndarray:
        n = xb.shape[0]
        if n <= self.train_size:
            return xb
        rng = np.random.default_rng(12345)
        idx = rng.integers(0, n, size=self.train_size, dtype=np.int64)
        return xb[idx]

    def _build_index(self):
        self._ensure_faiss()

        d = self.dim
        quantizer = faiss.IndexFlatL2(d)
        ivfpq = faiss.IndexIVFPQ(quantizer, d, self.nlist, self.m, self.nbits)

        try:
            ivfpq.nprobe = self.nprobe
        except Exception:
            pass

        try:
            ivfpq.use_precomputed_table = 1
        except Exception:
            pass

        try:
            ivfpq.cp.niter = 10
            ivfpq.cp.seed = 1234
        except Exception:
            pass

        base_index = ivfpq
        if self.use_opq:
            try:
                opq = faiss.OPQMatrix(d, self.m)
                base_index = faiss.IndexPreTransform(opq, ivfpq)
            except Exception:
                base_index = ivfpq

        try:
            index = faiss.IndexRefineFlat(base_index)
        except Exception:
            index = base_index

        try:
            index.verbose = False
        except Exception:
            pass

        try:
            index.k_factor = self.k_factor
        except Exception:
            pass

        self._index = index

    def _set_search_params(self):
        if faiss is None or self._index is None:
            return
        try:
            ivf = faiss.extract_index_ivf(self._index)
            if ivf is not None:
                ivf.nprobe = self.nprobe
        except Exception:
            pass

        try:
            base = self._index
            if hasattr(base, "base_index"):
                base = base.base_index
            if hasattr(base, "index"):
                base = base.index
            if hasattr(base, "nprobe"):
                base.nprobe = self.nprobe
        except Exception:
            pass

        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

    def _maybe_train_and_flush_pending(self):
        if self._trained:
            return
        if self._pending_count <= 0:
            return

        xb_all = np.vstack(self._pending) if len(self._pending) > 1 else self._pending[0]
        xb_all = self._as_f32_c(xb_all)

        if xb_all.shape[0] < self.nlist:
            return

        if self._index is None:
            self._build_index()

        xt = self._train_sample(xb_all)
        try:
            self._index.train(xt)
        except Exception:
            # fallback: build a flat index if training fails
            d = self.dim
            self._index = faiss.IndexFlatL2(d)
            self._trained = True
            self._index.add(xb_all)
            self._pending = []
            self._pending_count = 0
            return

        self._trained = True
        self._index.add(xb_all)

        self._pending = []
        self._pending_count = 0

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_f32_c(xb)
        if xb.size == 0:
            return

        if faiss is None:
            # Minimal fallback (slow); included for robustness.
            if self._index is None:
                self._index = xb.copy()
            else:
                self._index = np.vstack([self._index, xb])
            self._trained = True
            return

        if not self._trained:
            self._pending.append(xb)
            self._pending_count += xb.shape[0]
            if self._pending_count >= self.min_train:
                self._maybe_train_and_flush_pending()
            return

        if self._index is None:
            self._build_index()
            self._trained = False
            self._pending = [xb]
            self._pending_count = xb.shape[0]
            self._maybe_train_and_flush_pending()
            return

        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            return (
                np.empty((xq.shape[0], 0), dtype=np.float32),
                np.empty((xq.shape[0], 0), dtype=np.int64),
            )

        xq = self._as_f32_c(xq)
        nq = xq.shape[0]

        if faiss is None:
            # Slow fallback brute-force.
            if self._index is None or (isinstance(self._index, np.ndarray) and self._index.shape[0] == 0):
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._index
            xq2 = (xq * xq).sum(axis=1, keepdims=True)
            xb2 = (xb * xb).sum(axis=1, keepdims=True).T
            dots = xq @ xb.T
            dists = xq2 + xb2 - 2.0 * dots
            idx = np.argpartition(dists, kth=min(k - 1, dists.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dsel = dists[row, idx]
            order = np.argsort(dsel, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dsel[row, order].astype(np.float32, copy=False)
            return D, I

        if not self._trained:
            self._maybe_train_and_flush_pending()

        if self._index is None or (hasattr(self._index, "ntotal") and self._index.ntotal == 0):
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        self._set_search_params()

        D, I = self._index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.shape != (nq, k) or I.shape != (nq, k):
            D = np.ascontiguousarray(D.reshape(nq, k).astype(np.float32, copy=False))
            I = np.ascontiguousarray(I.reshape(nq, k).astype(np.int64, copy=False))
        return D, I