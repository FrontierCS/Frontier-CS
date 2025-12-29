import os
from typing import Tuple, Optional
import numpy as np
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        # Threading
        try:
            faiss.omp_set_num_threads(min(8, max(1, os.cpu_count() or 8)))
        except Exception:
            pass

        # Parameters with sensible defaults for high recall within latency budget
        self.algorithm: str = kwargs.get("algorithm", "hnswrefine")  # options: hnsw, hnswrefine, ivf_flat
        self.M: int = int(kwargs.get("M", 32))
        self.ef_construction: int = int(kwargs.get("ef_construction", 200))
        self.ef_search: int = int(kwargs.get("ef_search", 600))
        self.refine_factor: int = int(kwargs.get("refine_factor", 32))  # for IndexRefineFlat
        
        self.nlist: int = int(kwargs.get("nlist", 16384))
        self.nprobe: int = int(kwargs.get("nprobe", 200))
        self.max_train_points: int = int(kwargs.get("max_train_points", 262144))

        # Build underlying FAISS index placeholder
        self.index: Optional[faiss.Index] = None
        self.built = False

        # Create the index according to algorithm
        if self.algorithm == "hnsw":
            base = faiss.IndexHNSWFlat(self.dim, self.M)
            base.hnsw.efConstruction = self.ef_construction
            base.hnsw.efSearch = self.ef_search
            self.index = base
        elif self.algorithm == "hnswrefine":
            base = faiss.IndexHNSWFlat(self.dim, self.M)
            base.hnsw.efConstruction = self.ef_construction
            base.hnsw.efSearch = self.ef_search
            refine = faiss.IndexRefineFlat(base)
            refine.k_factor = max(1, self.refine_factor)
            self.index = refine
        elif self.algorithm == "ivf_flat":
            quantizer = faiss.IndexFlatL2(self.dim)
            ivf = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            ivf.nprobe = self.nprobe
            self.index = ivf
        else:
            # Fallback to HNSW refine if unknown algorithm
            base = faiss.IndexHNSWFlat(self.dim, self.M)
            base.hnsw.efConstruction = self.ef_construction
            base.hnsw.efSearch = self.ef_search
            refine = faiss.IndexRefineFlat(base)
            refine.k_factor = max(1, self.refine_factor)
            self.index = refine

    def _maybe_train_ivf(self, xb: np.ndarray) -> None:
        if not isinstance(self.index, faiss.IndexIVF):
            return
        ivf: faiss.IndexIVF = self.index
        if ivf.is_trained:
            return
        # Use a subset for training if needed
        train_x = xb
        if train_x.shape[0] > self.max_train_points:
            idx = np.random.RandomState(123).choice(train_x.shape[0], self.max_train_points, replace=False)
            train_x = train_x[idx]
        ivf.train(train_x)

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if isinstance(self.index, faiss.IndexIVF):
            self._maybe_train_ivf(xb)

        self.index.add(xb)
        self.built = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        # Ensure runtime parameters
        if isinstance(self.index, faiss.IndexHNSWFlat):
            self.index.hnsw.efSearch = self.ef_search
        elif isinstance(self.index, faiss.IndexRefineFlat):
            # base is HNSWFlat
            base = self.index.base_index
            if isinstance(base, faiss.IndexHNSWFlat):
                base.hnsw.efSearch = self.ef_search
            self.index.k_factor = max(1, self.refine_factor)
        elif isinstance(self.index, faiss.IndexIVF):
            self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, int(k))
        return D, I