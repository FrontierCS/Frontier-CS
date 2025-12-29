import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., nlist, nprobe, num_threads)
        """
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 1024))
        num_threads = kwargs.get("num_threads", 0)

        # Configure FAISS threading
        try:
            if num_threads is not None and num_threads > 0:
                faiss.omp_set_num_threads(int(num_threads))
            else:
                # Use maximum available threads
                max_threads = faiss.omp_get_max_threads()
                faiss.omp_set_num_threads(max_threads)
        except AttributeError:
            # Older FAISS versions may not expose omp controls; ignore
            pass

        self.index = None
        self.quantizer = None
        self.use_ivf = None  # True for IVF, False for Flat
        self._rng = np.random.default_rng(123)

    def _prepare_index(self, xb: np.ndarray) -> None:
        """
        Create and (if IVF) train the underlying FAISS index based on the
        initial batch of vectors `xb`.
        """
        N = xb.shape[0]

        # Use IVF for sufficiently large datasets; fall back to Flat for small ones.
        if N >= 2 * self.nlist:
            self.use_ivf = True
            self.quantizer = faiss.IndexFlatL2(self.dim)
            ivf_index = faiss.IndexIVFFlat(
                self.quantizer, self.dim, self.nlist, faiss.METRIC_L2
            )

            # Set search parameter
            ivf_index.nprobe = min(self.nprobe, self.nlist)

            # Train IVF with a reasonably large random subset
            n_train = min(N, 200000)
            if n_train < self.nlist:
                n_train = self.nlist

            if n_train == N:
                train_x = xb
            else:
                idx = self._rng.choice(N, size=n_train, replace=False)
                train_x = xb[idx]

            ivf_index.train(train_x)
            self.index = ivf_index
        else:
            # Small dataset: exact flat index is sufficient and simple.
            self.use_ivf = False
            self.index = faiss.IndexFlatL2(self.dim)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None or xb.size == 0:
            return

        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        if xb.ndim != 2 or xb.shape[1] != self.dim:
            xb = xb.reshape(-1, self.dim).astype(np.float32)

        if self.index is None:
            self._prepare_index(xb)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        if xq.ndim != 2 or xq.shape[1] != self.dim:
            xq = xq.reshape(-1, self.dim).astype(np.float32)

        nq = xq.shape[0]

        if self.index is None or self.index.ntotal == 0 or k <= 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        if self.use_ivf and hasattr(self.index, "nprobe"):
            self.index.nprobe = min(self.nprobe, getattr(self.index, "nlist", self.nprobe))

        k_eff = min(k, self.index.ntotal)
        D, I = self.index.search(xq, k_eff)

        if k_eff < k:
            D_pad = np.full((nq, k), np.inf, dtype=np.float32)
            I_pad = np.full((nq, k), -1, dtype=np.int64)
            D_pad[:, :k_eff] = D
            I_pad[:, :k_eff] = I
            D, I = D_pad, I_pad

        return D, I