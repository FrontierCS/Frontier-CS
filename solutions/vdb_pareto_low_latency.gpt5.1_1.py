import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 256))
        self.train_size = int(kwargs.get("train_size", 100000))
        self.index = None

        try:
            max_threads = faiss.omp_get_max_threads()
            num_threads = int(kwargs.get("num_threads", min(8, max_threads)))
            faiss.omp_set_num_threads(num_threads)
        except Exception:
            pass

    def _build_ivf_index(self, xb: np.ndarray) -> None:
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        n_train = min(self.train_size, xb.shape[0])
        if xb.shape[0] == n_train:
            train_x = xb
        else:
            rs = np.random.RandomState(123)
            idx = rs.choice(xb.shape[0], size=n_train, replace=False)
            train_x = xb[idx]

        index.train(train_x)
        index.add(xb)
        index.nprobe = min(self.nprobe, self.nlist)
        self.index = index

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2:
            raise ValueError("xb must be a 2D array")
        if xb.shape[1] != self.dim:
            raise ValueError(f"Dim mismatch in add: expected {self.dim}, got {xb.shape[1]}")

        xb = np.ascontiguousarray(xb, dtype=np.float32)

        if self.index is None:
            if xb.shape[0] >= self.nlist:
                self._build_ivf_index(xb)
            else:
                self.index = faiss.IndexFlatL2(self.dim)
                self.index.add(xb)
        else:
            ntotal = int(self.index.ntotal)
            try:
                is_flat = isinstance(self.index, faiss.IndexFlatL2)
            except Exception:
                is_flat = False

            if is_flat and ntotal < self.nlist and ntotal + xb.shape[0] >= self.nlist:
                old_xb = self.index.reconstruct_n(0, ntotal)
                all_xb = np.vstack((old_xb, xb))
                all_xb = np.ascontiguousarray(all_xb, dtype=np.float32)
                self._build_ivf_index(all_xb)
            else:
                self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None:
            raise RuntimeError("Index is empty. Call add() before search().")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2:
            raise ValueError("xq must be a 2D array")
        if xq.shape[1] != self.dim:
            raise ValueError(f"Dim mismatch in search: expected {self.dim}, got {xq.shape[1]}")

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        try:
            if isinstance(self.index, faiss.IndexIVF):
                self.index.nprobe = min(self.nprobe, getattr(self.index, "nlist", self.nprobe))
        except Exception:
            pass

        D, I = self.index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I
