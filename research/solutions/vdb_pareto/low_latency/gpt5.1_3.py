import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize an IVF-Flat index optimized for high recall under strict latency.
        """
        self.dim = dim

        # Hyperparameters (tuned for SIFT1M & low latency)
        self.nlist = int(kwargs.get("nlist", 8192))          # number of coarse clusters
        self.nprobe = int(kwargs.get("nprobe", 256))         # number of clusters to probe at search
        self.max_train_points = int(kwargs.get("max_train_points", 100000))
        random_seed = int(kwargs.get("random_seed", 123))

        self._rng = np.random.RandomState(random_seed)

        # Coarse quantizer
        self.quantizer = faiss.IndexFlatL2(dim)

        # IVF Flat index (exact distance inside lists, approximate via coarse quantizer)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)

        # Configure clustering/training parameters for speed and robustness
        self.index.cp.min_points_per_centroid = int(kwargs.get("min_points_per_centroid", 5))
        self.index.cp.niter = int(kwargs.get("niter", 20))

        # Configure search parameters
        self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index, training IVF on first call if needed.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype="float32")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        if not xb.flags["C_CONTIGUOUS"]:
            xb = np.ascontiguousarray(xb)

        # Train on first add if needed
        if not self.index.is_trained:
            n_train = min(self.max_train_points, xb.shape[0])
            if xb.shape[0] > n_train:
                idx = self._rng.choice(xb.shape[0], size=n_train, replace=False)
                train_x = xb[idx]
            else:
                train_x = xb

            self.index.train(train_x)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search k nearest neighbors for query vectors.
        """
        if k <= 0:
            raise ValueError("k must be positive")

        if not self.index.is_trained or self.index.ntotal == 0:
            raise RuntimeError("Index must be trained and contain vectors before calling search().")

        xq = np.asarray(xq, dtype="float32")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        if not xq.flags["C_CONTIGUOUS"]:
            xq = np.ascontiguousarray(xq)

        # Ensure search uses configured nprobe (can be overridden between calls via attribute)
        self.index.nprobe = self.nprobe

        distances, indices = self.index.search(xq, k)
        return distances, indices