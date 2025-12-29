import os
import numpy as np
from typing import Tuple

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs,
    ):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 16))
        self.quantizer_m = int(kwargs.get("quantizer_m", 32))
        self.ef_search = int(kwargs.get("ef_search", 64))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.max_train_points = int(kwargs.get("max_train_points", 200000))
        self.random_seed = int(kwargs.get("seed", 123))
        self.threads = int(kwargs.get("threads", max(1, min(8, os.cpu_count() or 1))))

        self._index = None
        self._rng = np.random.default_rng(self.random_seed)

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.threads)
            except Exception:
                pass

    def _create_index(self):
        # HNSW quantizer to accelerate coarse assignment
        quantizer = faiss.IndexHNSWFlat(self.dim, self.quantizer_m)
        quantizer.hnsw.efConstruction = self.ef_construction
        quantizer.hnsw.efSearch = self.ef_search

        # IVF-PQ index
        index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)
        return index

    def add(self, xb: np.ndarray) -> None:
        if faiss is None:
            raise RuntimeError("faiss is required for this solution")

        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)
        n, d = xb.shape
        if d != self.dim:
            raise ValueError(f"Dim mismatch: expected {self.dim}, got {d}")

        if self._index is None:
            self._index = self._create_index()

        if not self._index.is_trained:
            # Sample a subset for training
            train_size = min(self.max_train_points, n)
            if n > train_size:
                idx = self._rng.choice(n, size=train_size, replace=False)
                xtrain = xb[idx]
            else:
                xtrain = xb

            self._index.train(xtrain)

            # Ensure HNSW quantizer has centroids loaded after training
            # (Faiss handles this, but set efSearch again to be safe)
            try:
                self._index.quantizer.hnsw.efSearch = self.ef_search
            except Exception:
                pass

        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if faiss is None:
            raise RuntimeError("faiss is required for this solution")
        if self._index is None or self._index.ntotal == 0:
            raise RuntimeError("Index is empty. Call add() before search().")

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)
        nq, d = xq.shape
        if d != self.dim:
            raise ValueError(f"Dim mismatch: expected {self.dim}, got {d}")

        # Set search params
        self._index.nprobe = min(max(1, self.nprobe), self.nlist)
        try:
            self._index.quantizer.hnsw.efSearch = self.ef_search
        except Exception:
            pass

        D, I = self._index.search(xq, k)
        return D, I