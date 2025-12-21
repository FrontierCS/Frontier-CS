import numpy as np
from typing import Tuple

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self._added = 0

        self._use_faiss = faiss is not None
        if self._use_faiss:
            self.nlist = int(kwargs.get("nlist", 8192))
            if self.nlist <= 0:
                self.nlist = 1

            self.nprobe = int(kwargs.get("nprobe", 128))
            if self.nprobe <= 0:
                self.nprobe = 1

            self.training_samples = int(kwargs.get("training_samples", 100000))
            if self.training_samples <= 0:
                self.training_samples = 10000

            self.seed = int(kwargs.get("seed", 1234))
            self._rng = np.random.RandomState(self.seed)

            self.index = None
        else:
            # Fallback brute-force index (used only if faiss is unavailable)
            self.xb = None

    # ---------- FAISS-BASED IMPLEMENTATION ----------

    def _build_faiss_index(self, xb: np.ndarray) -> None:
        n, d = xb.shape
        if d != self.dim:
            raise ValueError(f"Expected vectors of dim {self.dim}, got {d}")

        # Choose number of IVF lists; cap by dataset size
        # For SIFT1M this will be 8192 (default).
        nlist = min(self.nlist, max(1, n // 100))
        ntrain = min(self.training_samples, n)
        if nlist > ntrain:
            nlist = ntrain

        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, faiss.METRIC_L2)

        # Training data: random subset for speed and robustness
        if n > ntrain:
            train_idx = self._rng.choice(n, size=ntrain, replace=False)
            train_x = xb[train_idx]
        else:
            train_x = xb

        if not train_x.flags["C_CONTIGUOUS"]:
            train_x = np.ascontiguousarray(train_x, dtype=np.float32)
        else:
            train_x = train_x.astype(np.float32, copy=False)

        index.train(train_x)
        index.nprobe = min(self.nprobe, nlist)
        self.index = index

    # ---------- PUBLIC API ----------

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2:
            raise ValueError("Input xb must be 2D (num_vectors, dim)")
        if xb.shape[1] != self.dim:
            raise ValueError(f"Expected xb.shape[1] == {self.dim}, got {xb.shape[1]}")

        if not xb.flags["C_CONTIGUOUS"]:
            xb = np.ascontiguousarray(xb, dtype=np.float32)

        if self._use_faiss:
            if self.index is None:
                self._build_faiss_index(xb)
            self.index.add(xb)
            self._added += xb.shape[0]
        else:  # brute-force fallback
            if self.xb is None:
                self.xb = xb.copy()
            else:
                self.xb = np.vstack([self.xb, xb])
            self._added += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._added == 0:
            raise RuntimeError("Index is empty. Call add() before search().")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2:
            raise ValueError("Input xq must be 2D (num_queries, dim)")
        if xq.shape[1] != self.dim:
            raise ValueError(f"Expected xq.shape[1] == {self.dim}, got {xq.shape[1]}")

        if not xq.flags["C_CONTIGUOUS"]:
            xq = np.ascontiguousarray(xq, dtype=np.float32)

        if self._use_faiss:
            self.index.nprobe = min(self.nprobe, getattr(self.index, "nlist", self.nprobe))
            distances, indices = self.index.search(xq, k)
            # Ensure correct dtypes
            if distances.dtype != np.float32:
                distances = distances.astype(np.float32)
            if indices.dtype != np.int64:
                indices = indices.astype(np.int64)
            return distances, indices
        else:
            # Brute-force L2 search (slow; only used if faiss is not available)
            xb = self.xb
            # Compute squared L2 distances in a vectorized way:
            # ||x - y||^2 = ||x||^2 + ||y||^2 - 2 x.y
            xq_sq = np.sum(xq ** 2, axis=1, keepdims=True)  # (nq, 1)
            xb_sq = np.sum(xb ** 2, axis=1, keepdims=True).T  # (1, nb)
            cross = xq @ xb.T  # (nq, nb)
            distances = xq_sq + xb_sq - 2.0 * cross

            # Get k smallest distances per query
            if k >= xb.shape[0]:
                k_eff = xb.shape[0]
            else:
                k_eff = k

            idx_part = np.argpartition(distances, k_eff - 1, axis=1)[:, :k_eff]
            row_indices = np.arange(distances.shape[0])[:, None]
            dist_part = distances[row_indices, idx_part]

            order = np.argsort(dist_part, axis=1)
            sorted_idx = idx_part[row_indices, order]
            sorted_dist = dist_part[row_indices, order]

            # If k_eff < k, pad with -1 and inf
            if k_eff < k:
                pad_size = k - k_eff
                pad_idx = -np.ones((xq.shape[0], pad_size), dtype=np.int64)
                pad_dist = np.full((xq.shape[0], pad_size), np.inf, dtype=np.float32)
                sorted_idx = np.concatenate([sorted_idx.astype(np.int64), pad_idx], axis=1)
                sorted_dist = np.concatenate([sorted_dist.astype(np.float32), pad_dist], axis=1)

            return sorted_dist.astype(np.float32), sorted_idx.astype(np.int64)
