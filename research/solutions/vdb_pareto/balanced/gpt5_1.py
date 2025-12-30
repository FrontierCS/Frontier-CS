import numpy as np
from typing import Tuple

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 192))
        self.training_samples = int(kwargs.get("training_samples", 200000))
        self.random_seed = int(kwargs.get("seed", 12345))
        self.metric = kwargs.get("metric", "l2")
        if self.metric.lower() not in ("l2", "l2sqr", "l2-squared"):
            self.metric = "l2"

        self.index = None
        self._is_trained = False
        self._ntotal = 0

        if faiss is None:
            # Minimal numpy fallback (inefficient, only for environments without faiss)
            self._xb = None
        else:
            try:
                max_threads = 8
                # Configure FAISS threads to match environment
                faiss.omp_set_num_threads(max_threads)
            except Exception:
                pass

            metric_type = faiss.METRIC_L2
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, metric_type)

            # For reproducibility in FAISS clustering/training
            try:
                faiss.cvar.rand_seed = self.random_seed
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dtype float32")

        if faiss is None or self.index is None:
            # Fallback: store data for brute force search
            if self._ntotal == 0:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            self._ntotal = self._xb.shape[0]
            return

        if not self._is_trained:
            # Sample training data
            n_train = min(self.training_samples, xb.shape[0])
            rng = np.random.RandomState(self.random_seed)
            if xb.shape[0] > n_train:
                idx = rng.choice(xb.shape[0], size=n_train, replace=False)
                xtrain = xb[idx]
            else:
                xtrain = xb

            self.index.train(xtrain)
            self._is_trained = True

        self.index.add(xb)
        self._ntotal = int(self.index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dtype float32")
        k = int(k)
        nq = xq.shape[0]

        if faiss is None or self.index is None:
            # Brute-force fallback (will be too slow for large N, only for robustness)
            if self._ntotal == 0:
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)
            xb = self._xb
            # Compute squared L2 distances in blocks to reduce memory
            bs = 1024
            D_all = np.empty((nq, xb.shape[0]), dtype=np.float32)
            for i in range(0, nq, bs):
                q = xq[i:i + bs]
                # (q - xb)^2 = ||q||^2 + ||xb||^2 - 2 q xb^T
                q_norm = (q ** 2).sum(axis=1, keepdims=True)
                xb_norm = (xb ** 2).sum(axis=1, keepdims=True).T
                D_block = q_norm + xb_norm - 2.0 * q.dot(xb.T)
                D_all[i:i + bs] = D_block.astype(np.float32)

            I = np.argpartition(D_all, kth=min(k - 1, D_all.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            Dk = D_all[row, I]
            order = np.argsort(Dk, axis=1)
            I = I[row, order]
            Dk = Dk[row, order]
            return Dk.astype(np.float32), I.astype(np.int64)

        if not self._is_trained or self._ntotal == 0:
            # No data
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # Ensure search parameter nprobe is set
        try:
            self.index.nprobe = self.nprobe
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32)
        if I.dtype != np.int64:
            I = I.astype(np.int64)
        return D, I