import os
import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters chosen to meet high recall >= 0.95 with low latency
        self.nlist = int(kwargs.get('nlist', 16384))
        self.nprobe = int(kwargs.get('nprobe', 64))
        self.training_samples = int(kwargs.get('training_samples', 250000))
        self.random_seed = int(kwargs.get('seed', 12345))
        # Set FAISS threads to available CPUs unless overridden
        num_threads = int(kwargs.get('num_threads', os.cpu_count() or 8))
        try:
            faiss.omp_set_num_threads(num_threads)
        except Exception:
            pass

        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = min(self.nprobe, self.nlist)
        self.ntotal = 0

    def _train_if_needed(self, xb: np.ndarray) -> None:
        if not self.index.is_trained:
            x = xb if xb.dtype == np.float32 else xb.astype(np.float32)
            n = x.shape[0]
            if n > self.training_samples:
                rng = np.random.default_rng(self.random_seed)
                idx = rng.choice(n, size=self.training_samples, replace=False)
                train = x[idx]
            else:
                train = x
            self.index.train(train)
            self.index.nprobe = min(self.nprobe, self.nlist)

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        self._train_if_needed(xb)
        self.index.add(xb)
        self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        self.index.nprobe = min(self.nprobe, self.nlist)
        D, I = self.index.search(xq, k)
        return D, I
