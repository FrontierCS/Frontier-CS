import os
from typing import Tuple

import numpy as np
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        IVF-Flat index optimized for high recall under latency constraints.
        """
        self.dim = int(dim)

        # IVF parameters with sensible defaults for SIFT1M
        self.nlist = int(kwargs.get("nlist", 4096))     # number of coarse centroids
        self.nprobe = int(kwargs.get("nprobe", 128))    # number of probes at search

        # Set FAISS to use all available threads, unless overridden
        num_threads = int(kwargs.get("num_threads", os.cpu_count() or 1))
        try:
            faiss.omp_set_num_threads(num_threads)
        except Exception:
            pass

        # Build IVF-Flat index with L2 metric
        quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

    def _fallback_to_flat(self):
        """Fallback to a flat index if IVF training is not appropriate."""
        flat = faiss.IndexFlatL2(self.dim)
        self.index = flat  # replace IVF index with flat index

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Handles training of IVF on first call.
        """
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        xb = np.ascontiguousarray(xb, dtype="float32")
        N, _ = xb.shape

        # If index is IVF and not yet trained, train it using a subset of xb
        if isinstance(self.index, faiss.IndexIVF) and not self.index.is_trained:
            # If dataset is too small for IVF, fallback to flat
            if N < self.nlist:
                self._fallback_to_flat()
                self.index.add(xb)
                return

            # Choose a training subset (Faiss recommends ~30-100x nlist, capped)
            target_train_size = max(self.nlist * 40, 100000)
            n_train = min(N, target_train_size)

            if N == n_train:
                train_x = xb
            else:
                # Sample without replacement
                indices = np.random.choice(N, n_train, replace=False)
                train_x = xb[indices]

            try:
                self.index.train(train_x)
            except Exception:
                # If training fails for any reason, fallback to flat
                self._fallback_to_flat()

        # Add all vectors to whichever index we currently have (IVF or flat)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        xq = np.ascontiguousarray(xq, dtype="float32")
        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        nq = xq.shape[0]
        ntotal = self.index.ntotal

        if ntotal == 0:
            # No data added yet: return empty/invalid results
            D = np.full((nq, k), np.inf, dtype="float32")
            I = np.full((nq, k), -1, dtype="int64")
            return D, I

        if k > ntotal:
            k = ntotal  # faiss can handle it, but we clamp to be safe

        D, I = self.index.search(xq, k)
        return D, I