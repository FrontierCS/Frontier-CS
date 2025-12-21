import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality
            **kwargs: Optional parameters:
                - nlist: number of IVF clusters (default: 4096)
                - M: number of PQ subquantizers (default: 16)
                - nbits: bits per PQ subquantizer (default: 8)
                - nprobe: IVF probes at search time (default: 8)
                - ivf_train_size: training set size for IVF/PQ (default: 120000)
                - min_ivf_size: minimum database size to use IVF (default: 50000)
                - random_seed: RNG seed for training sampling (default: 123)
        """
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.M = int(kwargs.get("M", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.nprobe = int(kwargs.get("nprobe", 8))
        self.ivf_train_size = int(kwargs.get("ivf_train_size", 120000))
        self.min_ivf_size = int(kwargs.get("min_ivf_size", 50000))
        self.random_seed = int(kwargs.get("random_seed", 123))

        self.index = None  # type: ignore
        self.is_ivf = False
        self.ntotal = 0
        self.rng = np.random.RandomState(self.random_seed)

    def _build_ivfpq(self, xb: np.ndarray) -> None:
        """
        Internal helper to build an IVF-PQ index on the given base vectors.
        """
        N, d = xb.shape
        # Heuristic: roughly 40 vectors per list, capped at self.nlist
        nlist = min(self.nlist, max(1, N // 40))
        train_size = min(self.ivf_train_size, N)

        if train_size < nlist:
            # Not enough data to train a robust IVF index; fall back to flat
            index = faiss.IndexFlatL2(d)
            index.add(xb)
            self.index = index
            self.is_ivf = False
            self.ntotal = N
            return

        # Coarse quantizer
        quantizer = faiss.IndexFlatL2(d)
        index = faiss.IndexIVFPQ(quantizer, d, nlist, self.M, self.nbits)

        # Training data
        if train_size == N:
            train_data = xb
        else:
            idx = self.rng.choice(N, size=train_size, replace=False)
            train_data = xb[idx].copy()

        index.train(train_data)
        index.add(xb)
        index.nprobe = min(self.nprobe, nlist)

        # Use precomputed tables if available (faster searches)
        if hasattr(index, "use_precomputed_table"):
            try:
                index.use_precomputed_table = True  # type: ignore[attr-defined]
            except Exception:
                pass

        self.index = index
        self.is_ivf = True
        self.ntotal = N

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype="float32")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (n, {self.dim})")

        n = xb.shape[0]
        if n == 0:
            return

        xb_c = np.ascontiguousarray(xb)

        if self.index is None:
            # First add call: decide index type based on dataset size
            if n >= self.min_ivf_size:
                self._build_ivfpq(xb_c)
            else:
                index = faiss.IndexFlatL2(self.dim)
                index.add(xb_c)
                self.index = index
                self.is_ivf = False
                self.ntotal = n
            return

        # Subsequent adds: just append to existing index
        self.index.add(xb_c)
        self.ntotal += n

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32
                - indices: shape (nq, k), dtype int64
        """
        xq = np.asarray(xq, dtype="float32")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        nq = xq.shape[0]
        xq_c = np.ascontiguousarray(xq)

        if self.index is None or self.ntotal == 0:
            # No data added
            D = np.full((nq, k), np.inf, dtype="float32")
            I = np.full((nq, k), -1, dtype="int64")
            return D, I

        k_eff = min(k, self.ntotal)
        D, I = self.index.search(xq_c, k_eff)

        if k_eff < k:
            # Pad with infinities / -1 if requested k > ntotal
            D_pad = np.full((nq, k), np.inf, dtype="float32")
            I_pad = np.full((nq, k), -1, dtype="int64")
            D_pad[:, :k_eff] = D
            I_pad[:, :k_eff] = I
            return D_pad, I_pad

        return D, I
