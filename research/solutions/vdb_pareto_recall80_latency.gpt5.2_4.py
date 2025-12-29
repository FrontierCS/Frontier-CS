import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


def _as_f32_contig(x: np.ndarray) -> np.ndarray:
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    if not x.flags["C_CONTIGUOUS"]:
        x = np.ascontiguousarray(x)
    return x


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.m = int(kwargs.get("m", 64))
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 4))

        self.train_size = int(kwargs.get("train_size", 200000))
        self.max_train_size = int(kwargs.get("max_train_size", self.train_size))

        self.n_threads = int(kwargs.get("n_threads", max(1, min(8, os.cpu_count() or 1))))

        if faiss is None:
            raise ImportError("faiss is required")

        try:
            faiss.omp_set_num_threads(self.n_threads)
        except Exception:
            pass

        self.index = None
        self._buffer = []
        self._buffer_rows = 0

    def _create_index(self):
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
        index.metric_type = faiss.METRIC_L2
        index.nprobe = self.nprobe
        try:
            index.use_precomputed_table = 1
        except Exception:
            pass
        try:
            index.parallel_mode = 0
        except Exception:
            pass
        self.index = index

    def _get_train_set_from_arrays(self, arrays, needed: int) -> np.ndarray:
        if needed <= 0:
            return None
        parts = []
        left = needed
        for a in arrays:
            if left <= 0:
                break
            if a.shape[0] <= left:
                parts.append(a)
                left -= a.shape[0]
            else:
                parts.append(a[:left])
                left = 0
        if not parts:
            return None
        if len(parts) == 1:
            t = parts[0]
            if not t.flags["C_CONTIGUOUS"]:
                t = np.ascontiguousarray(t)
            return t
        t = np.vstack(parts)
        if not t.flags["C_CONTIGUOUS"]:
            t = np.ascontiguousarray(t)
        return t

    def add(self, xb: np.ndarray) -> None:
        xb = _as_f32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim)")

        if self.index is None:
            self._create_index()

        if not self.index.is_trained:
            if self._buffer_rows == 0 and xb.shape[0] >= self.train_size:
                tsz = min(self.max_train_size, xb.shape[0])
                train = xb[:tsz]
                if not train.flags["C_CONTIGUOUS"]:
                    train = np.ascontiguousarray(train)
                self.index.train(train)
                self.index.add(xb)
                return

            self._buffer.append(xb)
            self._buffer_rows += xb.shape[0]

            if self._buffer_rows >= self.train_size:
                tsz = min(self.max_train_size, self._buffer_rows)
                train = self._get_train_set_from_arrays(self._buffer, tsz)
                self.index.train(train)
                for b in self._buffer:
                    self.index.add(b)
                self._buffer.clear()
                self._buffer_rows = 0
            return

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or (not self.index.is_trained and self._buffer_rows == 0):
            raise RuntimeError("Index is not initialized/trained; call add() first.")

        if self.index is not None and (not self.index.is_trained) and self._buffer_rows > 0:
            tsz = min(self.max_train_size, self._buffer_rows)
            train = self._get_train_set_from_arrays(self._buffer, tsz)
            self.index.train(train)
            for b in self._buffer:
                self.index.add(b)
            self._buffer.clear()
            self._buffer_rows = 0

        xq = _as_f32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim)")

        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I