import numpy as np
from typing import Tuple

try:
    import faiss
except ImportError:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        # Parameters tuned for SIFT1M with good recall/speed trade-off
        self.nlist = int(kwargs.get("nlist", 4096))   # number of IVF lists
        self.nprobe = int(kwargs.get("nprobe", 32))   # probes at search time
        self.m = int(kwargs.get("m", 16))             # PQ subquantizers
        self.nbits = int(kwargs.get("nbits", 8))      # bits per subquantizer

        self.use_faiss = faiss is not None
        self.index = None
        self._xb = None  # fallback storage if faiss is unavailable

        if self.use_faiss:
            # Optionally set number of threads
            n_threads = kwargs.get("n_threads", None)
            if hasattr(faiss, "omp_set_num_threads"):
                try:
                    if n_threads is None:
                        max_th = faiss.omp_get_max_threads() if hasattr(faiss, "omp_get_max_threads") else 0
                        if max_th and max_th > 0:
                            faiss.omp_set_num_threads(int(max_th))
                    else:
                        faiss.omp_set_num_threads(int(n_threads))
                except Exception:
                    pass

            index_desc = f"IVF{self.nlist},PQ{self.m}x{self.nbits}"
            self.index = faiss.index_factory(self.dim, index_desc, faiss.METRIC_L2)
        else:
            self.index = None

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            xb = xb.reshape(-1, self.dim)

        if self.use_faiss and self.index is not None:
            xb = np.ascontiguousarray(xb, dtype=np.float32)

            if not self.index.is_trained:
                # Train on a subset of xb for speed and quality
                target_train = max(self.nlist * 40, 100_000)
                n_train = min(xb.shape[0], target_train)

                if xb.shape[0] <= n_train:
                    train_x = xb
                else:
                    # Random subset without replacement
                    idx = np.random.choice(xb.shape[0], n_train, replace=False)
                    train_x = xb[idx]

                train_x = np.ascontiguousarray(train_x, dtype=np.float32)
                self.index.train(train_x)

            self.index.add(xb)
        else:
            # Naive fallback storage if faiss is not available
            xb = np.ascontiguousarray(xb, dtype=np.float32)
            if self._xb is None:
                self._xb = xb
            else:
                self._xb = np.vstack((self._xb, xb))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            xq = xq.reshape(-1, self.dim)

        if (
            self.use_faiss
            and self.index is not None
            and self.index.is_trained
            and getattr(self.index, "ntotal", 0) > 0
        ):
            self.index.nprobe = self.nprobe
            xq = np.ascontiguousarray(xq, dtype=np.float32)
            D, I = self.index.search(xq, k)

            if D.dtype != np.float32:
                D = D.astype(np.float32, copy=False)
            if I.dtype != np.int64:
                I = I.astype(np.int64, copy=False)
            return D, I

        # Fallback: exact search with NumPy (slow, for environments without faiss)
        if self._xb is None or self._xb.shape[0] == 0:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = -np.ones((nq, k), dtype=np.int64)
            return D, I

        xb = self._xb
        nq = xq.shape[0]
        N = xb.shape[0]

        # Compute full distance matrix (L2-squared)
        # distances[i, j] = ||xq[i] - xb[j]||^2
        xq_sq = np.sum(xq ** 2, axis=1, keepdims=True)        # (nq, 1)
        xb_sq = np.sum(xb ** 2, axis=1, keepdims=True).T      # (1, N)
        dots = xq @ xb.T                                      # (nq, N)
        distances = xq_sq + xb_sq - 2.0 * dots
        np.maximum(distances, 0.0, out=distances)

        if k >= N:
            indices = np.argsort(distances, axis=1)
            indices = indices[:, :k]
        else:
            indices = np.argpartition(distances, k - 1, axis=1)[:, :k]
            part_d = distances[np.arange(nq)[:, None], indices]
            order = np.argsort(part_d, axis=1)
            indices = indices[np.arange(nq)[:, None], order]

        final_distances = distances[np.arange(nq)[:, None], indices].astype(np.float32, copy=False)
        final_indices = indices.astype(np.int64, copy=False)

        return final_distances, final_indices
