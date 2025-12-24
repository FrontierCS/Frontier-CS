import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # Parameters with defaults, can be overridden via kwargs
        self.nlist = int(kwargs.get("nlist", 8192))
        self.pq_m = int(kwargs.get("pq_m", 16))
        self.pq_nbits = int(kwargs.get("pq_nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 4))
        self.train_samples = int(kwargs.get("train_samples", 262144))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_search = int(kwargs.get("hnsw_ef_search", 64))
        self.hnsw_ef_construction = int(kwargs.get("hnsw_ef_construction", 64))
        self.num_threads = int(kwargs.get("num_threads", 8))
        faiss.omp_set_num_threads(self.num_threads)

        # Build HNSW quantizer for coarse assignment
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
        quantizer.hnsw.efSearch = self.hnsw_ef_search
        quantizer.hnsw.efConstruction = self.hnsw_ef_construction

        # IVF-PQ index
        self.index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.pq_m, self.pq_nbits, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

        # Use precomputed tables for faster searches if available
        try:
            self.index.use_precomputed_table = True
        except Exception:
            pass

        # Residual encoding improves recall
        try:
            self.index.by_residual = True
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if not self.index.is_trained:
            n_train = min(self.train_samples, xb.shape[0])
            if n_train < xb.shape[0]:
                # Random uniform sampling for training
                rng = np.random.default_rng(123)
                idx = rng.choice(xb.shape[0], size=n_train, replace=False)
                xtrain = xb[idx]
            else:
                xtrain = xb
            self.index.train(xtrain)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)
        D, I = self.index.search(xq, k)
        return D, I
