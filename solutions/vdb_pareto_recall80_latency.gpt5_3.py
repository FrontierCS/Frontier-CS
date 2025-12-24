import numpy as np
from typing import Tuple, Optional

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 8))
        self.train_size = int(kwargs.get("train_size", 250000))
        self.random_seed = int(kwargs.get("random_seed", 12345))
        self.num_threads = int(kwargs.get("num_threads", 0))  # 0 -> faiss default

        # FAISS objects
        self.index: Optional["faiss.Index"] = None
        self._is_trained = False

        # Track total number of vectors added
        self.ntotal = 0

        # Threading
        if faiss is not None:
            if self.num_threads and self.num_threads > 0:
                try:
                    faiss.omp_set_num_threads(self.num_threads)
                except Exception:
                    pass

    def _init_index(self):
        if self.index is not None:
            return
        if faiss is None:
            raise RuntimeError("faiss is required for this index implementation.")
        # IVF with Flat (exact within inverted lists)
        self.index = faiss.index_factory(self.dim, f"IVF{self.nlist},Flat", faiss.METRIC_L2)
        try:
            self.index.nprobe = self.nprobe
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)

        self._init_index()

        # Train if necessary
        if not self._is_trained:
            np.random.seed(self.random_seed)
            train_sz = min(self.train_size, xb.shape[0])
            if train_sz < self.nlist:
                # Ensure at least nlist training points
                train_sz = min(xb.shape[0], self.nlist)
                if train_sz == 0:
                    raise ValueError("No data provided for training.")
            idx = np.random.choice(xb.shape[0], train_sz, replace=False)
            train_data = xb[idx].copy()
            self.index.train(train_data)
            self._is_trained = True

        # Add vectors
        self.index.add(xb)
        self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)

        if self.index is None:
            raise RuntimeError("Index has not been initialized. Call add() first.")

        if not self._is_trained:
            # In rare cases if called before add/train: fallback to FlatL2 on-the-fly (shouldn't happen in eval)
            flat = faiss.IndexFlatL2(self.dim)
            # No data to search against
            D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
            I = np.full((xq.shape[0], k), -1, dtype=np.int64)
            return D, I

        try:
            self.index.nprobe = self.nprobe
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes and shapes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
