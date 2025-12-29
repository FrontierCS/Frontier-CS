import numpy as np
from typing import Tuple, Optional

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters with sensible defaults for low-latency tier
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 6))
        self.pq_m = int(kwargs.get("pq_m", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.opq_m = int(kwargs.get("opq_m", self.pq_m))
        self.use_hnsw_coarse = bool(kwargs.get("use_hnsw_coarse", True))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.ef_search_coarse = int(kwargs.get("ef_search_coarse", 64))
        self.ef_construction_coarse = int(kwargs.get("ef_construction_coarse", 200))
        self.train_size = int(kwargs.get("train_size", 120000))
        self.clustering_niter = int(kwargs.get("clustering_niter", 12))
        self.seed = int(kwargs.get("seed", 123))
        self.num_threads = int(kwargs.get("num_threads", 0))  # 0 -> let faiss decide / use max

        # Internal state
        self._rng = np.random.RandomState(self.seed)
        self.index: Optional[faiss.Index] = None if faiss is not None else None
        self.ivf: Optional[faiss.IndexIVF] = None
        self.quantizer: Optional[faiss.Index] = None

        # Fallback storage in case faiss is not available (very slow, but ensures API)
        self._xb_fallback: Optional[np.ndarray] = None

        if faiss is not None:
            try:
                if self.num_threads > 0:
                    faiss.omp_set_num_threads(self.num_threads)
            except Exception:
                pass

    def _ensure_faiss(self):
        if faiss is None:
            raise RuntimeError("Faiss is required for this solution.")

    def _build_index(self, x_train: np.ndarray):
        self._ensure_faiss()
        d = self.dim

        if self.use_hnsw_coarse:
            quantizer = faiss.IndexHNSWFlat(d, self.hnsw_m)
            quantizer.hnsw.efSearch = self.ef_search_coarse
            quantizer.hnsw.efConstruction = self.ef_construction_coarse
        else:
            quantizer = faiss.IndexFlatL2(d)

        ivfpq = faiss.IndexIVFPQ(quantizer, d, self.nlist, self.pq_m, self.nbits, faiss.METRIC_L2)
        ivfpq.by_residual = True  # improves accuracy
        try:
            ivfpq.use_precomputed_table = 1  # speed-up if supported
        except Exception:
            pass

        # Tune clustering/training parameters to control build time
        try:
            ivfpq.cp.niter = self.clustering_niter
            # keep default max_points_per_centroid unless set via kwargs; using default is fine
        except Exception:
            pass

        if self.use_opq:
            opq = faiss.OPQMatrix(d, self.opq_m)
            opq.npca = d
            index = faiss.IndexPreTransform(opq, ivfpq)
        else:
            index = ivfpq

        # Train index
        index.train(x_train)

        # Store references
        self.index = index
        self.ivf = ivfpq
        self.quantizer = quantizer

        # Set runtime search params
        try:
            self.ivf.nprobe = self.nprobe
        except Exception:
            pass
        if self.use_hnsw_coarse:
            try:
                self.quantizer.hnsw.efSearch = self.ef_search_coarse
            except Exception:
                pass

    def _maybe_init_index(self, xb: np.ndarray):
        if self.index is not None:
            return

        # Prepare training data
        N = xb.shape[0]
        if N <= 0:
            # Should not happen, but guard anyway
            train = np.zeros((max(1, self.train_size // 10), self.dim), dtype=np.float32)
        else:
            train_sz = min(self.train_size, N)
            if N == train_sz:
                train = xb
            else:
                idx = self._rng.choice(N, size=train_sz, replace=False)
                train = xb[idx]
        self._build_index(train)

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) and dtype float32")

        if faiss is None:
            # Fallback: store data for brute-force search (slow)
            if self._xb_fallback is None:
                self._xb_fallback = xb.copy()
            else:
                self._xb_fallback = np.vstack((self._xb_fallback, xb))
            return

        if self.index is None or (self.ivf is not None and not self.ivf.is_trained):
            self._maybe_init_index(xb)

        # Add vectors
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) and dtype float32")
        if k <= 0:
            raise ValueError("k must be positive")

        if faiss is None:
            # Fallback: brute-force search (very slow)
            if self._xb_fallback is None or self._xb_fallback.shape[0] == 0:
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)
            xb = self._xb_fallback
            # Compute L2 distances using efficient formulation
            xq2 = np.sum(xq ** 2, axis=1, keepdims=True)
            xb2 = np.sum(xb ** 2, axis=1, keepdims=True).T
            distances = xq2 + xb2 - 2.0 * (xq @ xb.T)
            # Get top-k
            idx = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
            part = distances[np.arange(xq.shape[0])[:, None], idx]
            order = np.argsort(part, axis=1)
            idx = idx[np.arange(xq.shape[0])[:, None], order]
            D = distances[np.arange(xq.shape[0])[:, None], idx].astype(np.float32)
            I = idx.astype(np.int64)
            return D, I

        if self.index is None:
            # No data added
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # Ensure search params are set
        try:
            if self.ivf is not None:
                self.ivf.nprobe = self.nprobe
        except Exception:
            pass
        if self.use_hnsw_coarse and self.quantizer is not None:
            try:
                self.quantizer.hnsw.efSearch = self.ef_search_coarse
            except Exception:
                pass

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32)
        if I.dtype != np.int64:
            I = I.astype(np.int64)
        return D, I