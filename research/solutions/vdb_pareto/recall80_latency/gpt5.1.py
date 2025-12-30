import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Vector index using FAISS IVF-Flat (coarse quantization + exact search in lists).
        Optimized for fast batch queries with high recall.
        """
        self.dim = dim

        # IVF hyperparameters (tuned for SIFT1M; can be overridden via kwargs)
        self.nlist = int(kwargs.get("nlist", 4096))       # number of coarse clusters
        self.nprobe = int(kwargs.get("nprobe", 64))       # number of clusters to search
        self.train_size = int(kwargs.get("train_size", 100000))  # training sample size

        # Ensure sensible bounds
        if self.nlist <= 0:
            self.nlist = 4096
        if self.nprobe <= 0:
            self.nprobe = 64
        if self.train_size <= 0:
            self.train_size = 100000

        # Set FAISS threading if requested
        n_threads = kwargs.get("n_threads", None)
        if n_threads is not None:
            try:
                faiss.omp_set_num_threads(int(n_threads))
            except Exception:
                pass

        # Build quantizer and IVF index; training is delayed until data is added
        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

        # Internal state
        self._buffer = None       # buffer for vectors before training
        self._ntotal = 0          # total number of vectors in the FAISS index

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Training is triggered automatically
        once enough vectors have been accumulated.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dim=%d" % self.dim)

        n = xb.shape[0]
        if n == 0:
            return

        # If the index is not trained yet, accumulate vectors in a buffer
        if not self.index.is_trained:
            if self._buffer is None:
                # Make a contiguous copy to keep a stable buffer
                self._buffer = np.ascontiguousarray(xb, dtype=np.float32)
            else:
                # Accumulate until we have enough to train
                self._buffer = np.vstack((self._buffer, xb))

            # Only train when we have at least max(train_size, nlist) vectors
            if self._buffer.shape[0] >= max(self.train_size, self.nlist):
                n_train = min(self.train_size, self._buffer.shape[0])
                train_x = self._buffer[:n_train].astype(np.float32, copy=False)

                # Train IVF coarse quantizer
                self.index.train(train_x)

                # Add all buffered vectors to the trained index
                self.index.add(self._buffer.astype(np.float32, copy=False))
                self._ntotal = int(self.index.ntotal)

                # Release buffer
                self._buffer = None
        else:
            # Index already trained: add directly
            xb_c = np.ascontiguousarray(xb, dtype=np.float32)
            self.index.add(xb_c)
            self._ntotal = int(self.index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search k nearest neighbors for query vectors.
        Returns distances and indices arrays of shape (nq, k).
        """
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dim=%d" % self.dim)

        nq = xq.shape[0]
        if self.index is None or not self.index.is_trained or self._ntotal == 0:
            # No data available: return empty results
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xq_c = np.ascontiguousarray(xq, dtype=np.float32)
        # Ensure nprobe is set (in case user changed it after initialization)
        self.index.nprobe = self.nprobe

        D, I = self.index.search(xq_c, k)
        # Ensure numpy arrays of correct dtype
        if not isinstance(D, np.ndarray):
            D = np.array(D, dtype=np.float32)
        if not isinstance(I, np.ndarray):
            I = np.array(I, dtype=np.int64)
        return D, I