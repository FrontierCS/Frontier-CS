import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        """
        self.dim = int(dim)

        # IVF parameters tuned for SIFT1M / low-latency, high-recall
        self.desired_nlist = int(kwargs.get("nlist", 4096))
        self.base_nprobe = int(kwargs.get("nprobe", 64))

        # Training parameters
        self.max_train_points = int(kwargs.get("max_train_points", 200000))
        self.min_points_per_centroid = int(kwargs.get("min_points_per_centroid", 32))

        # Random seed for reproducible training sampling
        self.random_seed = int(kwargs.get("seed", 123))
        self.rng = np.random.RandomState(self.random_seed)

        # FAISS index instance (created on first add)
        self.index = None

        # Effective nprobe used for search (set after index creation)
        self.nprobe = min(self.base_nprobe, self.desired_nlist)

        # Optional: allow explicit control of FAISS threads
        num_threads = kwargs.get("num_threads", None)
        if num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                # If FAISS/OpenMP config fails, ignore and use defaults
                pass

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        xb = np.ascontiguousarray(xb, dtype="float32")
        if xb.ndim != 2:
            raise ValueError("Input xb must be a 2D array of shape (N, dim).")

        n, d = xb.shape
        if d != self.dim:
            raise ValueError(f"Dimensionality mismatch: index dim={self.dim}, xb dim={d}")

        if n == 0:
            return

        if self.index is None:
            # Determine the number of centroids (nlist) and training size based on data
            max_train = min(n, self.max_train_points)

            if max_train <= 0:
                return

            if max_train < self.min_points_per_centroid:
                # Very small dataset: one centroid per training point
                nlist = max_train
            else:
                # Ensure at least `min_points_per_centroid` training points per centroid
                nlist = max(self.desired_nlist, 1)
                nlist = min(nlist, max_train // self.min_points_per_centroid)
                if nlist < 1:
                    nlist = 1

            # Build IVF-Flat index
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFFlat(quantizer, self.dim, int(nlist), faiss.METRIC_L2)

            # Compute training set size: at least nlist, at most nlist * min_points_per_centroid, <= max_train
            target_train = nlist * self.min_points_per_centroid
            n_train = min(max_train, target_train)
            if n_train < nlist:
                n_train = nlist
            if n_train > n:
                n_train = n

            if n > n_train:
                train_idx = self.rng.choice(n, size=n_train, replace=False)
                xt = xb[train_idx]
            else:
                xt = xb

            index.train(xt)

            # Configure nprobe (cannot exceed nlist)
            self.nprobe = min(self.base_nprobe, nlist)
            index.nprobe = int(self.nprobe)

            self.index = index

        # Add all provided vectors to the index
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if self.index is None or not self.index.is_trained:
            raise RuntimeError("Index has not been initialized or trained before search.")

        if k <= 0:
            raise ValueError("k must be positive.")

        xq = np.ascontiguousarray(xq, dtype="float32")
        if xq.ndim != 2:
            raise ValueError("Input xq must be a 2D array of shape (nq, dim).")

        nq, d = xq.shape
        if d != self.dim:
            raise ValueError(f"Dimensionality mismatch: index dim={self.dim}, xq dim={d}")

        # Ensure nprobe is set correctly for IVF indices
        if hasattr(self.index, "nprobe"):
            self.index.nprobe = int(self.nprobe)

        D, I = self.index.search(xq, k)

        if not isinstance(D, np.ndarray):
            D = np.array(D)
        if not isinstance(I, np.ndarray):
            I = np.array(I)

        if D.dtype != np.float32:
            D = D.astype("float32")
        if I.dtype != np.int64:
            I = I.astype("int64")

        return D, I
