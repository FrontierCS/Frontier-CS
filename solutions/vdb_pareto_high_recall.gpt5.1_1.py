import numpy as np
from typing import Tuple

try:
    import faiss

    _FAISS_AVAILABLE = True
except Exception:  # pragma: no cover - fallback if faiss is not available
    faiss = None
    _FAISS_AVAILABLE = False


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        High-recall index for L2 similarity search.

        Uses Faiss HNSW-Flat by default (if available), with parameters tuned
        for high recall under a relaxed latency constraint. Falls back to a
        NumPy-based exact flat index if Faiss is unavailable.
        """
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 800))
        self.n_threads = int(kwargs.get("n_threads", 0))
        self.index_type = str(kwargs.get("index_type", "hnsw")).lower()

        self.use_faiss = _FAISS_AVAILABLE
        self.index = None  # Faiss index (if used)
        self.xb = None     # Fallback storage (NumPy flat index)

        if self.use_faiss:
            # Configure threads
            try:
                if self.n_threads <= 0:
                    self.n_threads = faiss.omp_get_max_threads()
                if self.n_threads > 0:
                    faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                # If OpenMP control is not available, ignore
                pass

            # Select index type
            if self.index_type == "flat":
                # Exact flat index (L2)
                self.index = faiss.IndexFlatL2(self.dim)
            else:
                # Default: HNSW-Flat index (approximate, high recall)
                self.index = faiss.IndexHNSWFlat(self.dim, self.M)
                try:
                    # Set HNSW construction and search parameters
                    self.index.hnsw.efConstruction = self.ef_construction
                    self.index.hnsw.efSearch = self.ef_search
                except Exception:
                    # In case attribute access fails in some faiss builds
                    pass

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Can be called multiple times.
        """
        if xb is None:
            return

        if not isinstance(xb, np.ndarray):
            xb = np.asarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        if self.use_faiss and self.index is not None:
            self.index.add(xb)
        else:
            # Fallback: store vectors for NumPy-based flat search
            if self.xb is None:
                self.xb = xb.copy()
            else:
                self.xb = np.vstack((self.xb, xb))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        Returns (distances, indices) with shapes (nq, k).
        """
        if not isinstance(xq, np.ndarray):
            xq = np.asarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")
        if k <= 0:
            raise ValueError("k must be positive")

        nq = xq.shape[0]

        # If Faiss index is available and initialized
        if self.use_faiss and self.index is not None:
            ntotal = int(self.index.ntotal)
            if ntotal == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            k_search = min(k, ntotal)

            # Ensure efSearch is set appropriately for HNSW
            try:
                if hasattr(self.index, "hnsw"):
                    # For larger k, increase efSearch a bit heuristically
                    target_ef = max(self.ef_search, k_search * 2)
                    self.index.hnsw.efSearch = int(target_ef)
            except Exception:
                pass

            D, I = self.index.search(xq, k_search)

            # Faiss already returns float32 / int64, but enforce dtypes
            D = np.asarray(D, dtype=np.float32)
            I = np.asarray(I, dtype=np.int64)

            if k_search == k:
                return D, I

            # Pad with +inf / -1 if requested k > ntotal
            D_padded = np.full((nq, k), np.inf, dtype=np.float32)
            I_padded = np.full((nq, k), -1, dtype=np.int64)
            D_padded[:, :k_search] = D
            I_padded[:, :k_search] = I
            return D_padded, I_padded

        # Fallback: NumPy-based exact flat search (L2-squared)
        if self.xb is None or self.xb.shape[0] == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xb = self.xb
        ntotal = xb.shape[0]
        k_search = min(k, ntotal)

        # Precompute norms of queries
        xq_sq = np.sum(xq.astype(np.float32) ** 2, axis=1, keepdims=True)

        # Initialize best distances/indices
        D_best = None
        I_best = None

        # Choose block size to limit memory (for distances matrix)
        # Max ~256MB for distance matrix (float32)
        max_block_bytes = 256 * 1024 * 1024
        bytes_per_elem = 4  # float32
        max_block_elems = max_block_bytes // bytes_per_elem
        # distances_block has shape (nq, block_size)
        block_size = max(1, min(ntotal, max_block_elems // max(1, nq)))

        for start in range(0, ntotal, block_size):
            end = min(start + block_size, ntotal)
            xb_block = xb[start:end].astype(np.float32, copy=False)

            # Compute squared L2 distances using expansion:
            # ||q - x||^2 = ||q||^2 + ||x||^2 - 2 q·x
            xb_block_sq = np.sum(xb_block ** 2, axis=1, keepdims=True).T  # (1, nb) -> (nb,)^T
            # (nq, nb)
            distances_block = xq_sq + xb_block_sq - 2.0 * (xq @ xb_block.T)

            # Get k_search best within this block for each query
            if end - start > k_search:
                idx_block = np.argpartition(distances_block, k_search - 1, axis=1)[:, :k_search]
            else:
                # If block smaller than k_search, take all
                idx_block = np.arange(end - start, dtype=np.int64)[None, :].repeat(nq, axis=0)

            part_dist = np.take_along_axis(distances_block, idx_block, axis=1)
            part_idx = idx_block + start

            if D_best is None:
                # Initialize with first block's candidates
                D_best = part_dist
                I_best = part_idx
            else:
                # Merge with existing best candidates
                D_comb = np.concatenate([D_best, part_dist], axis=1)
                I_comb = np.concatenate([I_best, part_idx], axis=1)

                if D_comb.shape[1] > k_search:
                    new_idx = np.argpartition(D_comb, k_search - 1, axis=1)[:, :k_search]
                    row_ids = np.arange(nq)[:, None]
                    D_best = D_comb[row_ids, new_idx]
                    I_best = I_comb[row_ids, new_idx]
                else:
                    D_best = D_comb
                    I_best = I_comb

        # Final sort of best distances
        order = np.argsort(D_best, axis=1)
        row_ids = np.arange(nq)[:, None]
        D_sorted = D_best[row_ids, order]
        I_sorted = I_best[row_ids, order]

        # Ensure shapes (nq, k) via padding if needed
        if k_search == k:
            return D_sorted.astype(np.float32, copy=False), I_sorted.astype(np.int64, copy=False)

        D_padded = np.full((nq, k), np.inf, dtype=np.float32)
        I_padded = np.full((nq, k), -1, dtype=np.int64)
        D_padded[:, :k_search] = D_sorted
        I_padded[:, :k_search] = I_sorted

        return D_padded, I_padded
