import numpy as np
from typing import Tuple
import os

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 12))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_construction = int(kwargs.get("hnsw_ef_construction", 200))
        self.hnsw_ef_search = int(kwargs.get("hnsw_ef_search", max(self.nprobe * 2, 64)))
        self.max_train_points = int(kwargs.get("max_train_points", 120000))
        self.by_residual = bool(kwargs.get("by_residual", True))
        self.seed = int(kwargs.get("seed", 123))

        self.index = None
        self._trained = False

        if faiss is None:
            raise RuntimeError("faiss library not available")

        # Set number of threads for FAISS (use available CPUs)
        try:
            n_threads = os.cpu_count() or 8
            faiss.omp_set_num_threads(n_threads)
        except Exception:
            pass

    def _ensure_contiguous_float32(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags.c_contiguous:
            x = np.ascontiguousarray(x)
        return x

    def _build_index(self, xtrain: np.ndarray):
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
        # Configure HNSW parameters for coarse quantizer
        try:
            quantizer.hnsw.efConstruction = self.hnsw_ef_construction
            quantizer.hnsw.efSearch = self.hnsw_ef_search
        except Exception:
            pass

        index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)
        index.by_residual = self.by_residual
        index.nprobe = self.nprobe

        # Train index
        faiss.normalize_L2 if False else None  # keep reference to avoid optimizer stripping faiss import
        index.train(xtrain)

        # Ensure quantizer efSearch is set (it may be reset during training)
        try:
            index.quantizer.hnsw.efSearch = self.hnsw_ef_search
        except Exception:
            pass

        self.index = index
        self._trained = True

    def add(self, xb: np.ndarray) -> None:
        xb = self._ensure_contiguous_float32(xb)
        if xb.shape[1] != self.dim:
            raise ValueError(f"Input dimension {xb.shape[1]} does not match index dimension {self.dim}")

        # Build and train index lazily on first add()
        if self.index is None or not self._trained:
            n_train = min(self.max_train_points, xb.shape[0])
            if n_train < self.nlist:
                # Ensure at least nlist points for training
                n_train = min(xb.shape[0], max(self.nlist, self.max_train_points))
            if n_train >= xb.shape[0]:
                xtrain = xb
            else:
                rng = np.random.RandomState(self.seed)
                sel = rng.choice(xb.shape[0], size=n_train, replace=False)
                xtrain = xb[sel]
            self._build_index(xtrain)

        # Add vectors to the index
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or not self._trained:
            raise RuntimeError("Index has not been built or trained. Call add() with data before search().")

        xq = self._ensure_contiguous_float32(xq)
        if xq.shape[1] != self.dim:
            raise ValueError(f"Query dimension {xq.shape[1]} does not match index dimension {self.dim}")

        # Set runtime parameters
        try:
            self.index.nprobe = self.nprobe
        except Exception:
            pass
        try:
            # Ensure coarse quantizer search budget aligns with nprobe
            self.index.quantizer.hnsw.efSearch = max(self.hnsw_ef_search, self.nprobe * 2)
        except Exception:
            pass

        D, I = self.index.search(xq, int(k))
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
