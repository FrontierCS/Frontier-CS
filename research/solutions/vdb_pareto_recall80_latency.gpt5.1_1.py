import numpy as np
from typing import Tuple

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        """
        self.dim = dim
        self.use_faiss = _FAISS_AVAILABLE

        # Common settings
        self._added = False

        if self.use_faiss:
            # IVF parameters tuned for SIFT1M / latency tier
            self.nlist = int(kwargs.get("nlist", 4096))
            self.nprobe = int(kwargs.get("nprobe", 64))
            self.num_train = int(kwargs.get("num_train", 100000))

            # Thread control
            try:
                max_threads = faiss.omp_get_max_threads()
            except Exception:
                max_threads = 1
            self.n_threads = int(kwargs.get("n_threads", max_threads))

            quantizer = faiss.IndexFlatL2(dim)
            self.index = faiss.IndexIVFFlat(quantizer, dim, self.nlist, faiss.METRIC_L2)
        else:
            # Fallback pure NumPy index (very slow, only for environments without faiss)
            self.index = None
            self.xb = None

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if self.use_faiss:
            xb = np.ascontiguousarray(xb, dtype=np.float32)

            # Ensure multithreading is enabled for training/add
            if self.n_threads is not None:
                try:
                    faiss.omp_set_num_threads(self.n_threads)
                except Exception:
                    pass

            if not self.index.is_trained:
                # Use a subset for training
                n_train = min(self.num_train, xb.shape[0])
                train_x = xb[:n_train].copy()
                self.index.train(train_x)

            self.index.add(xb)
        else:
            # Fallback: store vectors explicitly
            xb = np.ascontiguousarray(xb, dtype=np.float32)
            if self.xb is None:
                self.xb = xb.copy()
            else:
                self.xb = np.vstack((self.xb, xb))

        self._added = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if not self._added:
            raise RuntimeError("No vectors have been added to the index.")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if k <= 0:
            raise ValueError("k must be positive")

        if self.use_faiss:
            xq = np.ascontiguousarray(xq, dtype=np.float32)

            # Ensure multithreading for search
            if self.n_threads is not None:
                try:
                    faiss.omp_set_num_threads(self.n_threads)
                except Exception:
                    pass

            # Ensure nprobe is set (allow user override)
            self.index.nprobe = self.nprobe

            D, I = self.index.search(xq, k)
            # Faiss already returns float32 and int64 (or int32 in some builds)
            if I.dtype != np.int64:
                I = I.astype(np.int64)
            if D.dtype != np.float32:
                D = D.astype(np.float32)
            return D, I
        else:
            # Fallback brute-force L2 (squared) using NumPy
            xb = self.xb
            if xb is None or xb.shape[0] == 0:
                raise RuntimeError("No base vectors available for search.")

            N = xb.shape[0]
            if k > N:
                k = N

            xq = np.ascontiguousarray(xq, dtype=np.float32)
            xb = np.ascontiguousarray(xb, dtype=np.float32)

            # Compute L2 squared distances using (a-b)^2 = a^2 + b^2 - 2ab
            xq_norms = np.sum(xq ** 2, axis=1, keepdims=True)  # (nq, 1)
            xb_norms = np.sum(xb ** 2, axis=1, keepdims=True).T  # (1, N)
            # xq @ xb.T -> (nq, N)
            cross = xq @ xb.T
            distances = xq_norms + xb_norms - 2.0 * cross

            # Get k nearest via partial sort + full sort within k
            idx_part = np.argpartition(distances, k - 1, axis=1)[:, :k]
            part_distances = distances[np.arange(distances.shape[0])[:, None], idx_part]
            order = np.argsort(part_distances, axis=1)

            I = idx_part[np.arange(distances.shape[0])[:, None], order].astype(np.int64)
            D = part_distances[np.arange(distances.shape[0])[:, None], order].astype(np.float32)
            return D, I
