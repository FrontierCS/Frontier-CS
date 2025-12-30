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
        self.nprobe = int(kwargs.get("nprobe", 384))
        self.train_size = int(kwargs.get("train_size", 400_000))
        self.seed = int(kwargs.get("seed", 123))
        self.n_threads = int(kwargs.get("n_threads", min(8, (os.cpu_count() or 1))))

        if faiss is None:
            raise ImportError("faiss is required but could not be imported")

        faiss.omp_set_num_threads(max(1, self.n_threads))
        try:
            faiss.cvar.rand_seed = self.seed
        except Exception:
            pass

        self.index = faiss.index_factory(self.dim, f"IVF{self.nlist},Flat", faiss.METRIC_L2)
        if hasattr(self.index, "nprobe"):
            self.index.nprobe = max(1, min(self.nprobe, self.nlist))

        if hasattr(self.index, "cp"):
            try:
                self.index.cp.seed = self.seed
            except Exception:
                pass

        self._ntotal_added = 0

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim or xb.shape[0] == 0:
            return

        if not self.index.is_trained:
            n = xb.shape[0]
            ts = min(self.train_size, n)

            if ts < n:
                rng = np.random.default_rng(self.seed)
                idx = rng.choice(n, size=ts, replace=False)
                xtrain = np.ascontiguousarray(xb[idx])
            else:
                xtrain = xb

            self.index.train(xtrain)

        self.index.add(xb)
        self._ntotal_added += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            xq = np.asarray(xq)
            nq = int(xq.shape[0]) if xq.ndim >= 1 else 0
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim)")

        if (not self.index.is_trained) or (self.index.ntotal == 0):
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I