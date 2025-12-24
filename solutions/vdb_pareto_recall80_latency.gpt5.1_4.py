import numpy as np
from typing import Tuple
import faiss
import multiprocessing


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        IVF-Flat index optimized for latency under recall constraint.
        """
        self.dim = int(dim)

        # Parameters (can be overridden via kwargs)
        self.nlist = kwargs.get("nlist", None)          # number of coarse centroids
        self.nprobe = int(kwargs.get("nprobe", 16))     # number of probed lists at search
        self.train_size = int(kwargs.get("train_size", 100000))  # training subset size

        num_threads = kwargs.get("num_threads", None)
        if num_threads is None:
            try:
                num_threads = multiprocessing.cpu_count()
            except Exception:
                num_threads = 1
        self.num_threads = int(max(1, num_threads))

        # Set FAISS thread usage
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        self.quantizer = None
        self.index = None

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Trains IVF on first call.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2:
            xb = xb.reshape(-1, self.dim)
        xb = np.ascontiguousarray(xb)
        n, d = xb.shape

        if d != self.dim:
            raise ValueError(f"Dim mismatch: index dim={self.dim}, data dim={d}")

        if n == 0:
            return

        # Initialize and train index on first add
        if self.index is None:
            # Heuristic for nlist if not provided: min(4096, 4 * sqrt(N))
            if self.nlist is None:
                est = int(np.sqrt(max(1, n)))
                self.nlist = max(1, min(4096, 4 * est))
            self.nlist = int(max(1, min(self.nlist, n)))

            self.quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)

            # Set search parameter
            self.index.nprobe = int(max(1, min(self.nprobe, self.nlist)))

            # Train on a subset of xb
            train_size = min(self.train_size, n)
            xtrain = xb[:train_size]
            self.index.train(xtrain)

        # Add vectors to trained index
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search k nearest neighbors for query vectors.
        """
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2:
            xq = xq.reshape(-1, self.dim)
        xq = np.ascontiguousarray(xq)
        nq, d = xq.shape

        if d != self.dim:
            raise ValueError(f"Dim mismatch: index dim={self.dim}, query dim={d}")

        if self.index is None or self.index.ntotal == 0 or nq == 0 or k <= 0:
            distances = np.full((nq, k), np.inf, dtype=np.float32)
            indices = -np.ones((nq, k), dtype=np.int64)
            return distances, indices

        # Ensure FAISS uses desired number of threads
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        return D, I
