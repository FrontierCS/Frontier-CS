import os
from typing import Tuple
import numpy as np

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        if faiss is None:
            raise ImportError("faiss is required for this index.")
        self.dim = int(dim)
        # Algorithm selection (default to HNSW)
        self.algo = kwargs.get("algo", "hnsw").lower()

        # Threading
        self.num_threads = int(kwargs.get("num_threads", max(1, (os.cpu_count() or 8))))
        faiss.omp_set_num_threads(self.num_threads)

        # HNSW parameters
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 120))
        self.ef_search = int(kwargs.get("ef_search", 256))

        # IVF parameters (if used)
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 32))
        self._trained = False

        self.index = None
        self._build_index()

    def _build_index(self):
        if self.algo == "ivf_flat":
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            index.nprobe = self.nprobe
            self.index = index
        else:
            # Default to HNSW Flat
            index = faiss.IndexHNSWFlat(self.dim, self.M)
            index.hnsw.efConstruction = self.ef_construction
            index.hnsw.efSearch = self.ef_search
            self.index = index

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
            # Train on a subset to keep training time reasonable
            ntrain = min(100000, xb.shape[0])
            if xb.shape[0] > ntrain:
                # random subset for training
                idx = np.random.choice(xb.shape[0], ntrain, replace=False)
                train_vecs = xb[idx]
            else:
                train_vecs = xb
            self.index.train(train_vecs)
            self._trained = True

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        # Ensure parameters are set for search
        if hasattr(self.index, "hnsw"):
            self.index.hnsw.efSearch = self.ef_search
        if isinstance(self.index, faiss.IndexIVFFlat):
            self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, int(k))

        # Ensure output types
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I
