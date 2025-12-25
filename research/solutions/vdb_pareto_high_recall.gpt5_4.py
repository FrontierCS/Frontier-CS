import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        if faiss is None:
            raise ImportError("faiss library is required for this index implementation.")

        self.dim = int(dim)

        # Parameters with sensible defaults for high recall under relaxed latency
        self.nlist = int(kwargs.get("nlist", 8192))
        self.m = int(kwargs.get("m", 16))  # PQ subquantizers
        self.nbits = int(kwargs.get("nbits", 8))  # bits per code
        self.nprobe = int(kwargs.get("nprobe", 256))
        self.k_factor = int(kwargs.get("k_factor", 512))  # refinement candidates multiplier for k
        self.opq_m = int(kwargs.get("opq_m", 16))  # OPQ subspaces; set to 0 to disable OPQ

        # Training settings
        self.train_size = int(kwargs.get("train_size", 262144))  # number of vectors to train on
        self.random_train = bool(kwargs.get("random_train", True))
        self.seed = int(kwargs.get("seed", 123))

        # Thread settings
        num_threads = int(kwargs.get("num_threads", os.cpu_count() or 8))
        try:
            faiss.omp_set_num_threads(max(1, num_threads))
        except Exception:
            pass

        # Build the FAISS index pipeline: [OPQ] -> IVFPQ -> RefineFlat(FlatL2)
        self.index = self._build_index()
        self._ivf_index = self._find_ivf(self.index)

        # Book-keeping
        self._is_trained = False
        self._ntotal = 0

    def _build_index(self):
        d = self.dim

        # Coarse quantizer
        quantizer = faiss.IndexFlatL2(d)

        # Product Quantization index inside IVF
        ivfpq = faiss.IndexIVFPQ(quantizer, d, self.nlist, self.m, self.nbits)
        # Speed tweaks
        try:
            ivfpq.use_precomputed_table = 1
        except Exception:
            pass

        base_index = ivfpq

        # Optional OPQ pre-transform
        if self.opq_m and self.opq_m > 0:
            opq = faiss.OPQMatrix(d, self.opq_m)
            try:
                opq.niter = 20
                opq.verbose = False
            except Exception:
                pass
            base_index = faiss.IndexPreTransform(opq, base_index)

        # Refinement with exact L2 on top of the approximate index
        refine_index = faiss.IndexRefineFlat(base_index, faiss.IndexFlatL2(d))
        # Set k_factor for refinement
        if hasattr(refine_index, "k_factor"):
            try:
                refine_index.k_factor = float(self.k_factor)
            except Exception:
                pass

        return refine_index

    def _find_ivf(self, index):
        # Try using FAISS helper if available
        try:
            ivf = faiss.extract_index_ivf(index)
            if ivf is not None:
                return ivf
        except Exception:
            pass

        # Fallback recursive search
        try:
            # downcast if possible
            down = faiss.downcast_index(index)
            if isinstance(down, faiss.IndexIVF):
                return down
        except Exception:
            pass

        # Explore common wrappers
        if hasattr(index, "base_index"):
            ivf = self._find_ivf(index.base_index)
            if ivf is not None:
                return ivf
        if hasattr(index, "index"):
            ivf = self._find_ivf(index.index)
            if ivf is not None:
                return ivf

        return None

    def _ensure_trained(self, xb: np.ndarray):
        if self._is_trained:
            return

        xbt = np.ascontiguousarray(xb, dtype=np.float32)
        n_train = min(self.train_size, xbt.shape[0])

        if self.random_train and xbt.shape[0] > n_train:
            rng = np.random.RandomState(self.seed)
            idx = rng.choice(xbt.shape[0], n_train, replace=False)
            train_x = xbt[idx]
        else:
            train_x = xbt[:n_train]

        if not self.index.is_trained:
            self.index.train(train_x)

        self._is_trained = True

    def _set_search_params(self):
        # Set nprobe on the underlying IVF index if available
        if self._ivf_index is not None and hasattr(self._ivf_index, "nprobe"):
            try:
                self._ivf_index.nprobe = int(self.nprobe)
            except Exception:
                pass

        # Set k_factor on refine index (if not already)
        if hasattr(self.index, "k_factor"):
            try:
                self.index.k_factor = float(self.k_factor)
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        xba = np.ascontiguousarray(xb, dtype=np.float32)

        if not self._is_trained:
            self._ensure_trained(xba)

        self.index.add(xba)
        self._ntotal += xba.shape[0]

        # After data addition, ensure search params are set
        self._set_search_params()

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32)
        xqa = np.ascontiguousarray(xq, dtype=np.float32)

        self._set_search_params()

        D, I = self.index.search(xqa, int(k))

        # Ensure output dtypes and shapes
        D = np.ascontiguousarray(D, dtype=np.float32)
        I = np.ascontiguousarray(I, dtype=np.int64)
        return D, I
