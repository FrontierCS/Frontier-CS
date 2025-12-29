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
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.max_train = int(kwargs.get("max_train", 100000))
        self.flat_threshold = int(kwargs.get("flat_threshold", 50000))
        self.use_ivf = bool(kwargs.get("use_ivf", True))

        threads = kwargs.get("threads", None)
        if threads is None:
            threads = os.cpu_count() or 1
            threads = min(8, int(threads))
        self.threads = int(threads)

        if faiss is None:
            raise ImportError("faiss is required for this solution")

        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        self._index = None
        self._pending = []
        self._ntotal = 0

    def _as_f32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _sample_train_vectors(self, arrays, max_train: int) -> np.ndarray:
        total = int(sum(a.shape[0] for a in arrays))
        if total <= 0:
            return np.empty((0, self.dim), dtype=np.float32)

        if total <= max_train:
            x = np.vstack(arrays) if len(arrays) > 1 else arrays[0]
            return self._as_f32_contig(x)

        sizes = np.array([a.shape[0] for a in arrays], dtype=np.int64)
        props = sizes / float(total)
        target = np.maximum(1, (props * max_train).astype(np.int64))

        sampled = []
        taken = 0
        for a, t in zip(arrays, target):
            n = int(a.shape[0])
            t = min(int(t), n)
            if t <= 0:
                continue
            step = max(1, n // t)
            s = a[::step][:t]
            sampled.append(s)
            taken += s.shape[0]

        if taken < max_train:
            i_largest = int(np.argmax(sizes))
            a = arrays[i_largest]
            need = max_train - taken
            n = int(a.shape[0])
            if need > 0 and n > 0:
                step = max(1, n // need)
                s = a[1::step][:need] if n > 1 else a[:need]
                sampled.append(s)

        x = np.vstack(sampled) if len(sampled) > 1 else sampled[0]
        if x.shape[0] > max_train:
            x = x[:max_train]
        return self._as_f32_contig(x)

    def _build_from_pending(self) -> None:
        if self._index is not None:
            return

        if self._ntotal <= 0:
            self._index = faiss.IndexFlatL2(self.dim)
            self._pending.clear()
            return

        if (not self.use_ivf) or (self._ntotal < self.nlist) or (self._ntotal <= self.flat_threshold):
            index = faiss.IndexFlatL2(self.dim)
            for a in self._pending:
                index.add(a)
            self._index = index
            self._pending.clear()
            return

        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        try:
            index.cp.niter = int(getattr(index.cp, "niter", 15))
            if index.cp.niter > 15:
                index.cp.niter = 15
            index.cp.max_points_per_centroid = int(getattr(index.cp, "max_points_per_centroid", 256))
        except Exception:
            pass

        try:
            index.parallel_mode = 1
        except Exception:
            pass

        try:
            index.nprobe = int(self.nprobe)
        except Exception:
            pass

        xtrain = self._sample_train_vectors(self._pending, self.max_train)
        if xtrain.shape[0] < self.nlist:
            index_fallback = faiss.IndexFlatL2(self.dim)
            for a in self._pending:
                index_fallback.add(a)
            self._index = index_fallback
            self._pending.clear()
            return

        index.train(xtrain)
        for a in self._pending:
            index.add(a)

        self._index = index
        self._pending.clear()

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_f32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        n = int(xb.shape[0])
        if n <= 0:
            return

        if self._index is None:
            self._pending.append(xb)
            self._ntotal += n
            if self._ntotal >= max(self.nlist, self.flat_threshold):
                self._build_from_pending()
            return

        self._index.add(xb)
        self._ntotal += n

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = self._as_f32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if self._index is None:
            self._build_from_pending()

        try:
            if hasattr(self._index, "nprobe"):
                self._index.nprobe = int(self.nprobe)
        except Exception:
            pass

        D, I = self._index.search(xq, int(k))
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I