import numpy as np
from typing import Tuple

try:
    import faiss
except Exception as e:
        faiss = None


class Recall80LatencyIndex:
    def __init__(self, dim: int, **kwargs):
        if faiss is None:
            raise ImportError("faiss is required for this index")

        self.dim = dim
        # Parameters with sensible defaults
        self.nlist = int(kwargs.get("nlist", 4096))           # number of coarse clusters
        self.m = int(kwargs.get("m", 16))                     # number of PQ subvectors
        self.nbits = int(kwargs.get("nbits", 8))              # bits per PQ code (8 bits default)
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))           # HNSW graph degree for coarse quantizer
        self.nprobe = int(kwargs.get("nprobe", 6))            # number of coarse lists to probe at search
        self.train_size = int(kwargs.get("train_size", 100000))  # training subset size
        self.random_state = int(kwargs.get("random_state", 123))
        self.num_threads = int(kwargs.get("num_threads", 0))  # 0 => keep Faiss default
        self.quantizer_ef_search = int(kwargs.get("quantizer_ef_search", max(2 * self.nprobe, 64)))
        self.quantizer_ef_construction = int(kwargs.get("quantizer_ef_construction", 200))
        self.index_key = kwargs.get("index_key", None)

        # Build index
        if self.index_key is None:
            # Prefer IVF with HNSW quantizer and PQ for fast scanning
            # PQ{m} implies 8 bits by default; explicit 'x{nbits}' if not 8
            pq_part = f"PQ{self.m}" if self.nbits == 8 else f"PQ{self.m}x{self.nbits}"
            self.index_key = f"IVF{self.nlist}_HNSW{self.hnsw_m},{pq_part}"

        # Create index using index_factory; fallback if HNSW quantizer not available
        self.index = None
        self._hnsw_quantizer_used = False
        try:
            self.index = faiss.index_factory(self.dim, self.index_key, faiss.METRIC_L2)
            # Check if quantizer is HNSW
            try:
                if hasattr(self.index, "quantizer"):
                    q = self.index.quantizer
                    if hasattr(q, "hnsw"):
                        self._hnsw_quantizer_used = True
                        q.hnsw.efSearch = self.quantizer_ef_search
                        q.hnsw.efConstruction = self.quantizer_ef_construction
            except Exception:
                pass
        except Exception:
            # Fallback to IVF+PQ with flat quantizer
            pq_part = f"PQ{self.m}" if self.nbits == 8 else f"PQ{self.m}x{self.nbits}"
            fallback_key = f"IVF{self.nlist},{pq_part}"
            self.index = faiss.index_factory(self.dim, fallback_key, faiss.METRIC_L2)
            self._hnsw_quantizer_used = False

        # Tuning parameters
        try:
            if hasattr(self.index, "nprobe"):
                self.index.nprobe = self.nprobe
        except Exception:
            pass

        # Try enabling precomputed tables for IVFPQ if available
        try:
            if hasattr(self.index, "use_precomputed_table"):
                self.index.use_precomputed_table = 1
        except Exception:
            pass

        # Set FAISS threads if specified
        try:
            if self.num_threads and self.num_threads > 0:
                faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        self._is_trained = bool(getattr(self.index, "is_trained", False))
        self._ntotal = 0
        self._rng = np.random.RandomState(self.random_state)

    def _ensure_float32(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            return x.astype(np.float32, copy=False)
        return x

    def _train_if_needed(self, xb: np.ndarray) -> None:
        if self._is_trained:
            return
        # Sample training data
        n = xb.shape[0]
        if n <= 0:
            return
        train_size = min(self.train_size, n)
        if train_size < self.nlist:
            train_size = min(max(self.nlist * 4, self.nlist), n)
        if train_size < 1024:
            train_size = min(max(1024, self.nlist), n)

        if train_size == n:
            x_train = xb
        else:
            idx = self._rng.choice(n, train_size, replace=False)
            x_train = xb[idx]

        x_train = self._ensure_float32(x_train)
        try:
            self.index.train(x_train)
        except Exception:
            # If training fails (rare), fall back to a simpler index: HNSW flat
            hnsw = faiss.IndexHNSWFlat(self.dim, max(12, self.hnsw_m))
            hnsw.hnsw.efSearch = max(16, self.nprobe * 3)
            hnsw.hnsw.efConstruction = max(100, self.quantizer_ef_construction)
            self.index = hnsw

        # Apply parameters again after training (for IVFPQ it might reset)
        try:
            if hasattr(self.index, "nprobe"):
                self.index.nprobe = self.nprobe
        except Exception:
            pass
        try:
            if hasattr(self.index, "quantizer") and hasattr(self.index.quantizer, "hnsw"):
                self.index.quantizer.hnsw.efSearch = self.quantizer_ef_search
                self.index.quantizer.hnsw.efConstruction = self.quantizer_ef_construction
        except Exception:
            pass

        self._is_trained = bool(getattr(self.index, "is_trained", False))

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(self._ensure_float32(xb))
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dtype float32")
        self._train_if_needed(xb)
        self.index.add(xb)
        self._ntotal = int(self.index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.ascontiguousarray(self._ensure_float32(xq))
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dtype float32")
        if k <= 0:
            raise ValueError("k must be positive")
        if not self._is_trained and hasattr(self.index, "is_trained") and not self.index.is_trained:
            # In case no vectors were added before search
            raise RuntimeError("Index is not trained")

        # Ensure nprobe is set (in case user changed self.nprobe after training)
        try:
            if hasattr(self.index, "nprobe"):
                self.index.nprobe = self.nprobe
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        # Ensure types
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I