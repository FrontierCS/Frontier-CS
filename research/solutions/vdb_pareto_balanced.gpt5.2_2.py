import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.train_size = int(kwargs.get("train_size", 100000))
        self.seed = int(kwargs.get("seed", 12345))

        nt = kwargs.get("n_threads", None)
        if nt is None:
            nt = os.cpu_count() or 1
        self.n_threads = int(max(1, nt))

        if faiss is None:
            raise RuntimeError("faiss is required in this environment")

        try:
            faiss.omp_set_num_threads(self.n_threads)
        except Exception:
            pass

        self._rng = np.random.default_rng(self.seed)

        quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = min(self.nprobe, self.nlist)

        self._ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")
        if not xb.flags["C_CONTIGUOUS"]:
            xb = np.ascontiguousarray(xb)

        if not self.index.is_trained:
            n = xb.shape[0]
            ts = min(self.train_size, n)
            if ts <= 0:
                raise ValueError("No training data provided")
            if ts == n:
                train_x = xb
            else:
                idx = self._rng.choice(n, size=ts, replace=False)
                train_x = xb[idx]
                if not train_x.flags["C_CONTIGUOUS"]:
                    train_x = np.ascontiguousarray(train_x)
            self.index.train(train_x)

        self.index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")
        if self._ntotal == 0:
            nq = 0 if xq is None else int(np.asarray(xq).shape[0])
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")
        if not xq.flags["C_CONTIGUOUS"]:
            xq = np.ascontiguousarray(xq)

        self.index.nprobe = min(self.nprobe, self.nlist)

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I