import numpy as np
import faiss
import os
from typing import Tuple

class HighRecallIVFIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 16384))
        self.nprobe = int(kwargs.get("nprobe", 512))
        self.train_samples = int(kwargs.get("train_samples", 200000))
        self.random_seed = int(kwargs.get("seed", 123))
        self.index = None
        self.ntotal = 0

        # Configure FAISS threading conservatively to match environment
        try:
            num_threads = kwargs.get("num_threads", None)
            if num_threads is None:
                cpu_count = os.cpu_count() or 1
                num_threads = min(8, max(1, cpu_count))
            faiss.omp_set_num_threads(int(num_threads))
        except Exception:
            pass

    def _build_index(self, xb: np.ndarray):
        d = self.dim
        quantizer = faiss.IndexFlatL2(d)
        index = faiss.IndexIVFFlat(quantizer, d, self.nlist, faiss.METRIC_L2)

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        nxb = xb.shape[0]

        # Ensure sufficient training samples; sample without replacement
        train_n = min(nxb, max(self.train_samples, self.nlist * 40))
        if train_n < self.nlist:
            train_n = self.nlist  # faiss requires train_n >= nlist

        if train_n < nxb:
            rng = np.random.default_rng(self.random_seed)
            idx = rng.choice(nxb, size=train_n, replace=False)
            xtrain = xb[idx]
        else:
            xtrain = xb

        index.train(xtrain)
        index.add(xb)
        index.nprobe = min(self.nprobe, self.nlist)
        self.index = index
        self.ntotal += nxb

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return
        if self.index is None:
            self._build_index(xb)
        else:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
            if not self.index.is_trained:
                # Fallback: train on incoming batch if not trained
                train_n = min(xb.shape[0], max(self.train_samples, self.nlist * 40))
                if train_n < self.nlist:
                    train_n = self.nlist
                if train_n < xb.shape[0]:
                    rng = np.random.default_rng(self.random_seed)
                    idx = rng.choice(xb.shape[0], size=train_n, replace=False)
                    xtrain = xb[idx]
                else:
                    xtrain = xb
                self.index.train(xtrain)
            self.index.add(xb)
            self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or self.ntotal == 0:
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        self.index.nprobe = min(self.nprobe, self.nlist)
        D, I = self.index.search(xq, int(k))
        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)
