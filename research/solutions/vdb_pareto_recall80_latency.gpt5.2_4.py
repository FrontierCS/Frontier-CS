import os
import numpy as np
from typing import Tuple, Optional

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs,
    ):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 16384))
        self.nprobe = int(kwargs.get("nprobe", 16))
        self.m = int(kwargs.get("m", 32))
        self.nbits = int(kwargs.get("nbits", 8))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.ef_search = int(kwargs.get("ef_search", max(64, self.nprobe * 8)))
        self.ef_construction = int(kwargs.get("ef_construction", 80))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.use_precomputed_tables = bool(kwargs.get("use_precomputed_tables", True))

        n_threads = kwargs.get("n_threads", None)
        if n_threads is None:
            n_threads = os.cpu_count() or 8
        self.n_threads = int(max(1, min(8, n_threads)))

        self._buffers = []
        self._buffer_rows = 0

        self._index = None
        self._trained = False

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

    def _ensure_faiss(self):
        if faiss is None:
            raise RuntimeError("faiss is required for this solution")

    def _as_float32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _build_index(self, train_x: np.ndarray) -> None:
        self._ensure_faiss()
        d = self.dim

        quantizer = faiss.IndexHNSWFlat(d, self.hnsw_m)
        try:
            quantizer.hnsw.efSearch = int(self.ef_search)
            quantizer.hnsw.efConstruction = int(self.ef_construction)
        except Exception:
            pass

        index = faiss.IndexIVFPQ(quantizer, d, self.nlist, self.m, self.nbits)
        index.nprobe = int(self.nprobe)
        try:
            index.verbose = False
        except Exception:
            pass

        train_x = self._as_float32_contig(train_x)
        index.train(train_x)

        if self.use_precomputed_tables:
            try:
                index.use_precomputed_tables = 1
                index.precompute_table()
            except Exception:
                try:
                    index.use_precomputed_tables = 0
                except Exception:
                    pass

        self._index = index
        self._trained = True

    def _prepare_training_set(self, x: np.ndarray) -> np.ndarray:
        n = x.shape[0]
        if n <= self.train_size:
            return x
        step = max(1, n // self.train_size)
        train_x = x[::step]
        if train_x.shape[0] > self.train_size:
            train_x = train_x[: self.train_size]
        return train_x

    def _finalize_from_buffers_if_needed(self) -> None:
        if self._trained:
            if self._buffers:
                for b in self._buffers:
                    self._index.add(b)
                self._buffers.clear()
                self._buffer_rows = 0
            return

        if not self._buffers:
            raise RuntimeError("No data added to index")

        if len(self._buffers) == 1:
            all_x = self._buffers[0]
        else:
            all_x = np.vstack(self._buffers)

        train_x = self._prepare_training_set(all_x)
        self._build_index(train_x)
        self._index.add(all_x)

        self._buffers.clear()
        self._buffer_rows = 0

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_float32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

        if self._trained:
            self._index.add(xb)
            return

        self._buffers.append(xb)
        self._buffer_rows += xb.shape[0]

        if self._buffer_rows >= max(5000, self.train_size):
            self._finalize_from_buffers_if_needed()

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = self._as_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        self._finalize_from_buffers_if_needed()

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

        self._index.nprobe = int(self.nprobe)
        D, I = self._index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I