import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters with sensible defaults for recall >= 0.8 and very low latency
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 4))
        self.use_hnsw_quantizer = bool(kwargs.get("use_hnsw_quantizer", True))
        self.hnsw_m = int(kwargs.get("hnsw_m", 16))
        self.hnsw_ef_construction = int(kwargs.get("hnsw_ef_construction", 200))
        self.hnsw_ef_search = int(kwargs.get("hnsw_ef_search", 64))
        self.seed = int(kwargs.get("seed", 123))

        # Training sample size: ensure enough points per centroid for robust kmeans
        min_points_per_centroid = int(kwargs.get("min_points_per_centroid", 39))
        self.train_size = int(kwargs.get("train_size", max(self.nlist * min_points_per_centroid, 300000)))
        self.max_train_size = int(kwargs.get("max_train_size", 800000))

        # Threads
        self.num_threads = int(kwargs.get("num_threads", max(1, faiss.omp_get_max_threads())))
        faiss.omp_set_num_threads(self.num_threads)

        self.index = None
        self._quantizer_replaced = False
        self._rng = np.random.RandomState(self.seed)

    def _ensure_index(self):
        if self.index is None:
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            # Set nprobe default
            self.index.nprobe = self.nprobe

    def _replace_quantizer_with_hnsw(self):
        if self._quantizer_replaced or self.index is None:
            return
        # Extract centroids from current (Flat) quantizer
        try:
            qflat = self.index.quantizer
            centroids = faiss.vector_to_array(qflat.xb)
            if centroids.size == 0:
                return
            centroids = centroids.reshape(-1, self.dim)
            qhnsw = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
            qhnsw.hnsw.efConstruction = self.hnsw_ef_construction
            qhnsw.hnsw.efSearch = self.hnsw_ef_search
            qhnsw.add(centroids)
            self.index.quantizer = qhnsw
            self._quantizer_replaced = True
        except Exception:
            # Fallback: keep existing quantizer if anything goes wrong
            self._quantizer_replaced = False

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        assert xb.shape[1] == self.dim, "Input dim does not match index dim"

        self._ensure_index()

        if not self.index.is_trained:
            n = xb.shape[0]
            # Determine training sample size
            target_train = min(max(self.train_size, self.nlist * 39), self.max_train_size)
            target_train = min(target_train, n)
            if target_train <= 0:
                target_train = min(n, self.nlist * 39)

            if target_train < n:
                train_idx = self._rng.choice(n, size=target_train, replace=False)
                xtrain = xb[train_idx]
            else:
                xtrain = xb

            self.index.train(xtrain)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or not self.index.is_trained:
            # No data added; return empty results
            nq = xq.shape[0]
            return np.empty((nq, k), dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # Replace quantizer with HNSW for faster coarse search (after all adds)
        if self.use_hnsw_quantizer and not self._quantizer_replaced:
            self._replace_quantizer_with_hnsw()

        self.index.nprobe = self.nprobe

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        assert xq.shape[1] == self.dim, "Query dim does not match index dim"

        D, I = self.index.search(xq, int(k))
        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I