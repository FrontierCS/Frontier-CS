import numpy as np
from typing import Tuple

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs
    ):
        if faiss is None:
            raise ImportError("faiss is required for this solution.")
        self.dim = int(dim)

        # Parameters with sensible defaults for recall >= 0.8 and low latency
        self.nlist = int(kwargs.get("nlist", 8192))            # number of IVF clusters
        self.nprobe = int(kwargs.get("nprobe", 10))            # probes at search time
        self.pq_m = int(kwargs.get("M", 16))                   # PQ subquantizers
        self.pq_nbits = int(kwargs.get("pq_nbits", 8))         # bits per subquantizer
        self.use_opq = bool(kwargs.get("use_opq", True))       # OPQ transform before IVF-PQ
        self.use_refine = bool(kwargs.get("use_refine", True)) # refine with exact L2 on small shortlist
        self.refine_factor = int(kwargs.get("refine_factor", 4))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.random_seed = int(kwargs.get("seed", 123))
        self.num_threads = int(kwargs.get("threads", 0))       # 0 -> use faiss default

        # Internal handles
        self._index = None                   # top-level index used for add/search (may be refine wrapper)
        self._base = None                    # base index (possibly with pretransform), before refine
        self._ivf = None                     # extracted IVF pointer for parameter tuning
        self._is_trained = False

        # Configure threads if specified
        try:
            if self.num_threads and hasattr(faiss, "omp_set_num_threads"):
                faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

    def _build_base_index(self) -> None:
        # Build index via index_factory for simplicity and speed
        if self.use_opq:
            desc = f"OPQ{self.pq_m},IVF{self.nlist},PQ{self.pq_m}x{self.pq_nbits}"
        else:
            desc = f"IVF{self.nlist},PQ{self.pq_m}x{self.pq_nbits}"
        self._base = faiss.index_factory(self.dim, desc, faiss.METRIC_L2)

        # Extract IVF to tune training/search parameters
        self._ivf = faiss.extract_index_ivf(self._base)
        if self._ivf is None:
            # In unlikely cases, fall back to searching directly on _base
            self._ivf = None
        else:
            # Training parameters: reduce iterations to save time, ensure feasibility with fewer train pts
            try:
                self._ivf.cp.min_points_per_centroid = 5
                self._ivf.cp.max_points_per_centroid = 1000000000
                self._ivf.cp.niter = 15
            except Exception:
                pass

            # Precompute tables for faster scanning, if available
            try:
                self._ivf.use_precomputed_table = 1
            except Exception:
                pass

        # Optional refine (exact L2 re-ranking of a very small shortlist, improves recall with minimal cost)
        if self.use_refine and hasattr(faiss, "IndexRefineFlat"):
            refine = faiss.IndexRefineFlat(self._base)
            refine.k_factor = max(1, self.refine_factor)
            self._index = refine
        else:
            self._index = self._base

        # Set search parameters (nprobe) on the appropriate layer
        try:
            if self._ivf is not None:
                self._ivf.nprobe = self.nprobe
            else:
                # Try parameter space as a generic fallback
                ps = faiss.ParameterSpace()
                ps.set_index_parameter(self._index, "nprobe", self.nprobe)
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if self._index is None:
            self._build_base_index()

        # Train if needed
        if not self._index.is_trained:
            n = xb.shape[0]
            rng = np.random.default_rng(self.random_seed)
            if n <= self.train_size:
                train_x = xb
            else:
                # Sample without replacement for training
                idx = rng.choice(n, size=self.train_size, replace=False)
                idx.sort()
                train_x = xb[idx]
            self._index.train(train_x)
            self._is_trained = True

        # Add vectors
        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq is None or xq.size == 0:
            return (np.empty((0, k), dtype=np.float32), np.empty((0, k), dtype=np.int64))
        if self._index is None:
            # Build minimal flat index if add() wasn't called (shouldn't happen in evaluator)
            flat = faiss.IndexFlatL2(self.dim)
            self._index = flat
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        # Ensure nprobe is correctly set
        try:
            if self._ivf is not None:
                self._ivf.nprobe = self.nprobe
            else:
                ps = faiss.ParameterSpace()
                ps.set_index_parameter(self._index, "nprobe", self.nprobe)
        except Exception:
            pass

        D, I = self._index.search(xq, int(k))
        # Ensure output dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I