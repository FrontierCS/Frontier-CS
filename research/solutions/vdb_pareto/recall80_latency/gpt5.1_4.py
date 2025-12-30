import numpy as np
from typing import Tuple

try:
    import faiss

    _FAISS_AVAILABLE = True
except Exception:
    _FAISS_AVAILABLE = False


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        nlist: int = 2048,
        nprobe: int = 8,
        train_size: int = 262144,
        num_threads: int = None,
        **kwargs,
    ):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality.
            nlist: Number of IVF clusters (lists).
            nprobe: Number of clusters to search at query time.
            train_size: Number of vectors to use for training (if training is required).
            num_threads: Number of threads for Faiss (if None, uses Faiss default).
            **kwargs: Optional overrides for nlist, nprobe, train_size, num_threads.
        """
        self.dim = dim

        # Allow overriding via kwargs (for evaluator flexibility)
        if "nlist" in kwargs:
            nlist = int(kwargs["nlist"])
        if "nprobe" in kwargs:
            nprobe = int(kwargs["nprobe"])
        if "train_size" in kwargs:
            train_size = int(kwargs["train_size"])
        if "num_threads" in kwargs and kwargs["num_threads"] is not None:
            num_threads = int(kwargs["num_threads"])

        self.nlist = int(nlist)
        self.nprobe = int(nprobe)
        self.train_size = int(train_size)

        self._use_faiss = _FAISS_AVAILABLE

        if self._use_faiss:
            # Configure threads
            try:
                if num_threads is None:
                    num_threads = faiss.omp_get_max_threads()
                faiss.omp_set_num_threads(num_threads)
            except Exception:
                pass

            # Build IVF-Flat index (coarse quantizer + exact L2 in lists)
            quantizer = faiss.IndexFlatL2(dim)
            self.index = faiss.IndexIVFFlat(quantizer, dim, self.nlist, faiss.METRIC_L2)
            self.index.nprobe = self.nprobe
        else:
            # Fallback: brute-force storage (very slow for 1M vectors, only used if Faiss missing)
            self.index = None
            self.xb = None

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        xb = np.ascontiguousarray(xb)

        if self._use_faiss:
            # Train IVF quantizer on a subset if not yet trained
            if not self.index.is_trained:
                n_train = min(self.train_size, xb.shape[0])
                train_data = xb[:n_train]
                self.index.train(train_data)
            self.index.add(xb)
        else:
            # Brute-force fallback: just store vectors
            if self.xb is None:
                self.xb = xb.copy()
            else:
                self.xb = np.vstack((self.xb, xb))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32.
            k: Number of nearest neighbors to return.

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32 (L2 distances)
                - indices: shape (nq, k), dtype int64
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        xq = np.ascontiguousarray(xq)

        if self._use_faiss:
            # Ensure nprobe is set (in case caller changed it externally)
            self.index.nprobe = self.nprobe
            D, I = self.index.search(xq, k)
            return D, I
        else:
            # Brute-force fallback (extremely slow on large datasets)
            if self.xb is None or self.xb.shape[0] == 0:
                nq = xq.shape[0]
                return (
                    np.full((nq, k), np.inf, dtype=np.float32),
                    np.full((nq, k), -1, dtype=np.int64),
                )

            xb = self.xb
            # Compute squared L2 distances: ||xq - xb||^2
            # Using (a - b)^2 = a^2 + b^2 - 2ab
            xq_norms = (xq ** 2).sum(axis=1, keepdims=True)
            xb_norms = (xb ** 2).sum(axis=1, keepdims=True).T
            cross_term = xq @ xb.T
            distances = xq_norms + xb_norms - 2.0 * cross_term

            # Get k nearest neighbors
            if k >= xb.shape[0]:
                idx = np.argsort(distances, axis=1)
                D = np.take_along_axis(distances, idx, axis=1)
                I = idx
                return D[:, :k].astype(np.float32), I[:, :k].astype(np.int64)

            idx_part = np.argpartition(distances, k - 1, axis=1)[:, :k]
            part_dist = np.take_along_axis(distances, idx_part, axis=1)
            order = np.argsort(part_dist, axis=1)
            final_idx = np.take_along_axis(idx_part, order, axis=1)
            final_dist = np.take_along_axis(part_dist, order, axis=1)

            return final_dist.astype(np.float32), final_idx.astype(np.int64)