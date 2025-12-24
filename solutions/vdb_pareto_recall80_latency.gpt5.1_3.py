import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optional kwargs:
            - nlist: number of IVF cells (default: 4096)
            - nprobe: number of IVF cells to probe at search (default: 8)
            - max_train_points: max points used to train IVF (default: 100000)
            - use_ivf: whether to use IVF; if False, fall back to flat index (default: True)
        """
        self.dim = dim

        # IVF parameters
        self.nlist = int(kwargs.get("nlist", 4096))
        if self.nlist <= 0:
            self.nlist = 1

        self.nprobe = int(kwargs.get("nprobe", 8))
        if self.nprobe <= 0:
            self.nprobe = 1

        self.max_train_points = int(kwargs.get("max_train_points", 100000))
        if self.max_train_points <= 0:
            self.max_train_points = 100000

        self.use_ivf = bool(kwargs.get("use_ivf", True))

        seed = int(kwargs.get("seed", 123))
        self._rs = np.random.RandomState(seed)

        # FAISS index (created on first add)
        self.index = None
        self.ntotal = 0

        # Optionally allow user to control threads; otherwise keep FAISS defaults
        num_threads = kwargs.get("num_threads", None)
        if num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass

    def _create_flat_index(self) -> None:
        self.index = faiss.IndexFlatL2(self.dim)

    def _create_ivf_index(self, xb: np.ndarray) -> None:
        """
        Create and train an IVF index using xb as the (first) batch of data.
        """
        n, d = xb.shape
        if n <= 0 or d != self.dim:
            raise ValueError("Invalid training data for IVF index.")

        # Adjust nlist so it does not exceed number of training points
        effective_nlist = min(self.nlist, n)
        if effective_nlist <= 0:
            effective_nlist = 1
        self.nlist = effective_nlist

        quantizer = faiss.IndexFlatL2(self.dim)
        ivf = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        # Training set: random subset of xb (or all if small enough)
        n_train = min(self.max_train_points, n)
        if n_train < self.nlist:
            # Not enough points to train a reasonable IVF; fall back to flat
            self._create_flat_index()
            return

        if n > n_train:
            indices = self._rs.choice(n, n_train, replace=False)
            train_xb = xb[indices]
        else:
            train_xb = xb

        ivf.train(train_xb)
        ivf.nprobe = min(self.nprobe, self.nlist)
        self.index = ivf

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. On the first call, build and (if IVF) train the index.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        xb = np.ascontiguousarray(xb)
        n, _ = xb.shape

        if self.index is None:
            # Decide whether to use IVF or flat based on current batch size
            # For very small datasets, IVF is not beneficial.
            min_ivf_points = max(self.nlist * 4, 10000)
            if (not self.use_ivf) or n < min_ivf_points:
                self._create_flat_index()
            else:
                self._create_ivf_index(xb)

        # If creation fell back to flat index in _create_ivf_index, just add to it.
        # If IVF, index is already trained at this point.
        self.index.add(xb)
        self.ntotal = int(self.index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        xq = np.ascontiguousarray(xq)
        nq = xq.shape[0]
        requested_k = int(k)
        if requested_k <= 0:
            # Return empty results with proper shapes
            return (
                np.empty((nq, 0), dtype=np.float32),
                np.empty((nq, 0), dtype=np.int64),
            )

        if self.ntotal == 0 or self.index is None:
            # No data; return infinities and -1 indices
            D = np.full((nq, requested_k), np.inf, dtype=np.float32)
            I = -np.ones((nq, requested_k), dtype=np.int64)
            return D, I

        # Ensure k does not exceed ntotal for the FAISS call
        k_eff = min(requested_k, self.ntotal)
        D, I = self.index.search(xq, k_eff)

        # If k_eff < requested_k, pad with inf / -1
        if k_eff < requested_k:
            D_padded = np.full((nq, requested_k), np.inf, dtype=np.float32)
            I_padded = -np.ones((nq, requested_k), dtype=np.int64)
            D_padded[:, :k_eff] = D
            I_padded[:, :k_eff] = I
            D, I = D_padded, I_padded

        return D, I
