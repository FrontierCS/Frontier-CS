import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 16384))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.k_factor = int(kwargs.get("k_factor", 64))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.seed = int(kwargs.get("seed", 12345))

        self.num_threads = int(kwargs.get("num_threads", min(8, os.cpu_count() or 1)))
        self.min_train = int(kwargs.get("min_train", max(self.train_size, self.nlist * 10)))

        self._buffer = []
        self._buffer_ntotal = 0

        if faiss is None:
            raise RuntimeError("faiss is required for this solution")

        faiss.omp_set_num_threads(self.num_threads)

        quantizer = faiss.IndexFlatL2(self.dim)
        self.base = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
        self.base.nprobe = self.nprobe

        try:
            self.base.use_precomputed_table = 1
        except Exception:
            pass

        self.index = faiss.IndexRefineFlat(self.base)
        try:
            self.index.k_factor = self.k_factor
        except Exception:
            pass

    def _as_float32_c(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _train_from(self, xb: np.ndarray) -> None:
        n = xb.shape[0]
        if n <= 0:
            return

        sample_size = min(n, self.train_size)
        if sample_size < n:
            rs = np.random.RandomState(self.seed)
            idx = rs.choice(n, size=sample_size, replace=False)
            xtrain = xb[idx]
            if not xtrain.flags["C_CONTIGUOUS"]:
                xtrain = np.ascontiguousarray(xtrain)
        else:
            xtrain = xb

        self.index.train(xtrain)
        self.base.nprobe = self.nprobe
        try:
            self.index.k_factor = self.k_factor
        except Exception:
            pass

    def _ensure_trained_and_flush(self) -> None:
        if self.index.is_trained:
            if self._buffer_ntotal > 0:
                for b in self._buffer:
                    self.index.add(b)
                self._buffer.clear()
                self._buffer_ntotal = 0
            return

        if self._buffer_ntotal <= 0:
            return

        if len(self._buffer) == 1:
            xb_all = self._buffer[0]
        else:
            xb_all = np.vstack(self._buffer)
        self._train_from(xb_all)
        self.index.add(xb_all)
        self._buffer.clear()
        self._buffer_ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_float32_c(xb)
        n = xb.shape[0]
        if n == 0:
            return

        if self.index.is_trained:
            self.index.add(xb)
            return

        if self._buffer_ntotal == 0 and n >= self.min_train:
            self._train_from(xb)
            self.index.add(xb)
            return

        self._buffer.append(xb)
        self._buffer_ntotal += n
        if self._buffer_ntotal >= self.min_train:
            self._ensure_trained_and_flush()

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            nq = int(xq.shape[0])
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        if not self.index.is_trained and self._buffer_ntotal > 0:
            self._ensure_trained_and_flush()

        xq = self._as_float32_c(xq)

        self.base.nprobe = self.nprobe
        try:
            self.index.k_factor = self.k_factor
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I