import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs
    ):
        self.dim = dim

        # Parameters with sensible defaults aimed at high recall under tight latency
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 4))
        self.pq_m = int(kwargs.get("M", 16))
        self.pq_nbits = int(kwargs.get("nbits", 8))

        # HNSW quantizer params
        self.quantizer_m = int(kwargs.get("quantizer_m", 32))
        self.ef_search = int(kwargs.get("ef_search", 64))
        self.ef_construction = int(kwargs.get("ef_construction", 100))

        # OPQ transform
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.opq_m = int(kwargs.get("opq_m", self.pq_m))

        # Training control
        self.training_samples = int(kwargs.get("training_samples", 150000))
        self.training_seed = int(kwargs.get("training_seed", 123))

        # Training iterations tuning for speed/quality tradeoff
        self.coarse_niter = int(kwargs.get("coarse_niter", 15))

        # Threading
        self.num_threads = int(kwargs.get("num_threads", 0))  # 0 => faiss default

        self.index = None
        self.ivf = None  # Keep a reference to set/search parameters when wrapped
        self._is_trained = False

        if self.num_threads > 0:
            try:
                faiss.omp_set_num_threads(self.num_threads)
            except Exception:
                pass

    def _build_index(self):
        # Build HNSW quantizer for IVF coarse assignment
        quantizer = faiss.IndexHNSWFlat(self.dim, self.quantizer_m)
        quantizer.hnsw.efSearch = self.ef_search
        quantizer.hnsw.efConstruction = self.ef_construction

        # IVF with PQ codes
        ivf = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.pq_m, self.pq_nbits)
        ivf.nprobe = self.nprobe
        ivf.cp.min_points_per_centroid = 5
        ivf.cp.niter = self.coarse_niter
        # Enable use of precomputed tables for faster scanning
        ivf.use_precomputed_table = 1

        if self.use_opq:
            opq = faiss.OPQMatrix(self.dim, self.opq_m)
            opq.niter = 10
            index = faiss.IndexPreTransform(opq, ivf)
        else:
            index = ivf

        self.index = index
        self.ivf = ivf

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if self.index is None:
            self._build_index()

        if not self._is_trained:
            # Sample training data
            rng = np.random.default_rng(self.training_seed)
            n_train = min(self.training_samples, xb.shape[0])
            if xb.shape[0] == n_train:
                xt = xb
            else:
                idx = rng.choice(xb.shape[0], size=n_train, replace=False)
                xt = xb[idx]

            self.index.train(xt)
            self._is_trained = True

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        # Ensure runtime parameters are set (in case user changed attributes)
        if self.ivf is not None:
            self.ivf.nprobe = self.nprobe
            if isinstance(self.ivf.quantizer, faiss.IndexHNSWFlat):
                try:
                    self.ivf.quantizer.hnsw.efSearch = self.ef_search
                except Exception:
                    pass

        D, I = self.index.search(xq, k)
        return D, I