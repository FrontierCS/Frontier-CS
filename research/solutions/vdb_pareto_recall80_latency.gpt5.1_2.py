import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Vector index optimized for SIFT1M-like data using FAISS IVF-Flat.

        Args:
            dim: dimensionality of vectors
            **kwargs:
                nlist: number of IVF clusters (default: 8192)
                nprobe: number of clusters to probe at search (default: 32)
                use_pq: whether to use IVF-PQ instead of IVF-Flat (default: False)
                pq_m: number of subquantizers for PQ (default: 16)
                pq_nbits: bits per PQ subvector (default: 8)
                train_size: number of training vectors for k-means (default: 200000)
                random_seed: RNG seed for training sampling (default: 123)
                num_threads: if given, override FAISS OMP thread count
        """
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 32))
        self.use_pq = bool(kwargs.get("use_pq", False))
        self.pq_m = int(kwargs.get("pq_m", 16))
        self.pq_nbits = int(kwargs.get("pq_nbits", 8))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.random_seed = int(kwargs.get("random_seed", 123))

        self.num_threads = kwargs.get("num_threads", None)
        if self.num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

        self.index = None
        self.ntotal = 0

    def _build_index(self, xb: np.ndarray) -> None:
        n, d = xb.shape
        if d != self.dim:
            raise ValueError(f"Input dimensionality {d} does not match index dim {self.dim}")

        # Choose actual nlist based on dataset size to avoid too many empty lists
        max_nlist_by_size = max(1, n // 40)  # ~40 vectors per list minimum
        nlist = min(self.nlist, max_nlist_by_size)

        quantizer = faiss.IndexFlatL2(self.dim)
        if self.use_pq:
            index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, self.pq_m, self.pq_nbits)
            try:
                index.use_precomputed_table = True
            except Exception:
                pass
        else:
            index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, faiss.METRIC_L2)

        self.index = index

        # Train IVF index
        if not self.index.is_trained:
            train_size = min(self.train_size, n)
            if train_size < nlist:
                train_size = nlist
            if n > train_size:
                rs = np.random.RandomState(self.random_seed)
                idx = rs.choice(n, train_size, replace=False)
                train_x = xb[idx].copy()
            else:
                train_x = xb.copy()
            self.index.train(train_x)

        # Set nprobe (cannot exceed nlist)
        try:
            self.index.nprobe = min(self.nprobe, self.index.nlist)
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")
        n, _ = xb.shape

        if self.index is None:
            self._build_index(xb)

        self.index.add(xb)
        self.ntotal += n

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")
        nq = xq.shape[0]

        if self.index is None or self.ntotal == 0 or k <= 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        # Ensure nprobe is within valid bounds
        try:
            nprobe = self.nprobe
            if hasattr(self.index, "nlist"):
                nprobe = min(nprobe, self.index.nlist)
            if hasattr(self.index, "ntotal") and self.index.ntotal > 0:
                nprobe = min(nprobe, self.index.ntotal)
            self.index.nprobe = max(1, nprobe)
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        return D, I
