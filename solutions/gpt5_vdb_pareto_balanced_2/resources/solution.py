import numpy as np
from typing import Tuple, Optional
import faiss

class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs
    ):
        self.dim = dim

        # Parameters with sensible defaults aimed at high recall within latency constraints
        self.nlist: int = int(kwargs.get("nlist", 65536))
        self.nprobe: int = int(kwargs.get("nprobe", 96))
        self.hnsw_m: int = int(kwargs.get("M", kwargs.get("hnsw_m", 32)))
        self.ef_search: int = int(kwargs.get("ef_search", max(200, self.nprobe * 2)))
        self.ef_construction: int = int(kwargs.get("ef_construction", 200))
        self.train_size: int = int(kwargs.get("train_size", 200000))
        self.num_threads: Optional[int] = kwargs.get("num_threads", None)

        if self.num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

        # Build IVF-HNSW-Flat index (coarse quantizer = HNSW for fast centroid search)
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
        quantizer.hnsw.efConstruction = self.ef_construction
        quantizer.hnsw.efSearch = self.ef_search

        self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

        # Clustering params to keep training efficient
        try:
            cp = self.index.cp  # clustering parameters
            cp.niter = 20
            cp.min_points_per_centroid = 20
            cp.max_points_per_centroid = 1000
        except Exception:
            pass

        self._is_trained = False
        self._ntotal_added = 0

    def add(self, xb: np.ndarray) -> None:
        if xb is None or len(xb) == 0:
            return
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            xb = xb.reshape(-1, self.dim).astype(np.float32, copy=False)

        # Train on a subset of the first add call to keep training time reasonable
        if not self.index.is_trained:
            n = xb.shape[0]
            train_size = min(self.train_size, n)
            if train_size < self.nlist:
                # ensure at least one vector per centroid for training
                train_size = min(n, max(self.nlist, self.train_size))
            if train_size < n:
                # sample without replacement
                idx = np.random.RandomState(123).choice(n, train_size, replace=False)
                x_train = xb[idx].copy()
            else:
                x_train = xb.copy()

            self.index.train(x_train)
            # ensure efSearch is adequate after training
            try:
                self.index.quantizer.hnsw.efSearch = max(self.ef_search, self.nprobe * 2)
            except Exception:
                pass
            self.index.nprobe = self.nprobe

        self.index.add(xb)
        self._ntotal_added += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            xq = xq.reshape(-1, self.dim).astype(np.float32, copy=False)

        # Ensure search parameters are set
        try:
            self.index.quantizer.hnsw.efSearch = max(self.ef_search, self.nprobe * 2)
        except Exception:
            pass
        self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, k)
        return D, I
