import numpy as np
import faiss
import os
import math
import multiprocessing
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters (with sensible defaults)
        self.nlist = int(kwargs.get("nlist", 0))  # will be decided at first add if 0
        self.nprobe = int(kwargs.get("nprobe", 96))
        self.max_train_points = int(kwargs.get("max_train_points", 200000))
        self.random_seed = int(kwargs.get("seed", 12345))
        self._index = None
        self._trained = False
        self._added = 0
        # threading
        num_threads = kwargs.get("num_threads", None)
        if num_threads is None:
            try:
                num_threads = min(32, multiprocessing.cpu_count() or 1)
            except Exception:
                num_threads = 8
        try:
            faiss.omp_set_num_threads(int(num_threads))
        except Exception:
            pass
        # allow override via env var
        env_nprobe = os.environ.get("VDB_NPROBE")
        if env_nprobe is not None:
            try:
                self.nprobe = int(env_nprobe)
            except Exception:
                pass
        env_nlist = os.environ.get("VDB_NLIST")
        if env_nlist is not None:
            try:
                self.nlist = int(env_nlist)
            except Exception:
                pass
        np.random.seed(self.random_seed)
        try:
            faiss.cvar.rand_seed = self.random_seed
        except Exception:
            pass

    def _decide_nlist(self, N: int) -> int:
        if self.nlist > 0:
            return self.nlist
        # Heuristic for nlist based on dataset size
        # Favor power-of-two nlist values for efficiency
        if N >= 2_000_000:
            base = 16384
        elif N >= 1_000_000:
            base = 8192
        elif N >= 500_000:
            base = 4096
        elif N >= 200_000:
            base = 2048
        else:
            base = max(1024, int(4 * math.sqrt(max(N, 1))))
        # round to nearest power of two between 512 and 32768
        pow2 = 2 ** int(round(math.log2(max(512, min(base, 32768)))))
        return pow2

    def _build_index(self, xb: np.ndarray):
        N = xb.shape[0]
        nl = self._decide_nlist(N)
        self.nlist = nl
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, nl, faiss.METRIC_L2)
        index.nprobe = int(self.nprobe)
        self._index = index

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dim matching the index dimension")
        if self._index is None:
            self._build_index(xb)
        if not self._trained:
            # Train on a random subset (or all if small)
            ntrain = min(self.max_train_points, xb.shape[0])
            if xb.shape[0] > ntrain:
                idx = np.random.choice(xb.shape[0], size=ntrain, replace=False)
                train_x = xb[idx]
            else:
                train_x = xb
            self._index.train(train_x)
            self._trained = True
        self._index.add(xb)
        self._added += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._index is None or not self._trained or self._added == 0:
            raise RuntimeError("Index is not built or empty. Call add() with data before searching.")
        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dim matching the index dimension")
        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")
        self._index.nprobe = int(self.nprobe)
        D, I = self._index.search(xq, k)
        return D, I