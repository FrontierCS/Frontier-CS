import numpy as np
from typing import Tuple

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    _FAISS_AVAILABLE = False


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        """
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.train_size = int(kwargs.get("train_size", 100000))
        self.seed = int(kwargs.get("seed", 123))
        self.num_threads = kwargs.get("num_threads", None)

        self.use_faiss = _FAISS_AVAILABLE
        self.index = None  # faiss index, if used
        self.xb = None     # fallback storage if faiss is unavailable

        if self.use_faiss and self.num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        if xb is None:
            return

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        if self.use_faiss:
            self._add_faiss(xb)
        else:
            self._add_fallback(xb)

    def _add_faiss(self, xb: np.ndarray) -> None:
        n, _ = xb.shape

        if self.index is None:
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        if not self.index.is_trained:
            train_size = min(self.train_size, n)
            if train_size < n:
                rng = np.random.RandomState(self.seed)
                indices = rng.choice(n, train_size, replace=False)
                train_x = xb[indices]
            else:
                train_x = xb
            train_x = np.ascontiguousarray(train_x, dtype=np.float32)
            self.index.train(train_x)

        self.index.add(xb)
        self.index.nprobe = self.nprobe

    def _add_fallback(self, xb: np.ndarray) -> None:
        if self.xb is None:
            self.xb = xb.copy()
        else:
            self.xb = np.vstack((self.xb, xb))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        if self.use_faiss:
            if self.index is None or not self.index.is_trained:
                raise ValueError("FAISS index not initialized or not trained.")
            if self.num_threads is not None:
                try:
                    faiss.omp_set_num_threads(int(self.num_threads))
                except Exception:
                    pass
            self.index.nprobe = self.nprobe
            D, I = self.index.search(xq, k)
            if D.dtype != np.float32:
                D = D.astype(np.float32)
            if I.dtype != np.int64:
                I = I.astype(np.int64)
            return D, I
        else:
            return self._brute_force_search(xq, k)

    def _brute_force_search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fallback brute-force search using NumPy (inefficient for large datasets).
        """
        if self.xb is None:
            raise ValueError("No vectors added to the index.")

        xb = self.xb
        # Compute squared L2 distances
        diff = xq[:, None, :] - xb[None, :, :]
        distances = np.einsum('ijk,ijk->ij', diff, diff)

        # Partial sort to get top-k
        idx_part = np.argpartition(distances, k - 1, axis=1)[:, :k]
        part_dist = np.take_along_axis(distances, idx_part, axis=1)

        # Sort the top-k
        order = np.argsort(part_dist, axis=1)
        final_idx = np.take_along_axis(idx_part, order, axis=1).astype(np.int64)
        final_dist = np.take_along_axis(part_dist, order, axis=1).astype(np.float32)

        return final_dist, final_idx