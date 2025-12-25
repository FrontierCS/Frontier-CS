import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 128))
        self.train_size = int(kwargs.get("train_size", 100000))
        self.metric = faiss.METRIC_L2
        self.num_threads = int(kwargs.get("num_threads", max(1, faiss.omp_get_max_threads())))
        faiss.omp_set_num_threads(self.num_threads)

        self.index = None
        self.is_trained = False

    def _build_index(self):
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, self.metric)
        index.nprobe = self.nprobe
        return index

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)

        if self.index is None:
            self.index = self._build_index()

        if not self.index.is_trained:
            n_train = min(self.train_size, xb.shape[0])
            if n_train < self.nlist:
                n_train = min(max(self.nlist * 10, self.nlist), xb.shape[0])
            rs = np.random.RandomState(123)
            train_idx = rs.choice(xb.shape[0], n_train, replace=False)
            xt = xb[train_idx].copy()
            self.index.train(xt)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
        self.index.nprobe = self.nprobe
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32)
        if I.dtype != np.int64:
            I = I.astype(np.int64)
        return D, I
