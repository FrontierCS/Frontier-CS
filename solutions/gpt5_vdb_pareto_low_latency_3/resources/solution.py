import numpy as np
import faiss
from typing import Tuple, List, Optional
import os

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        # IVF-PQ configuration
        self.nlist = int(kwargs.get('nlist', 4096))
        self.m = int(kwargs.get('m', 16))
        self.nbits = int(kwargs.get('nbits', 8))
        self.nprobe = int(kwargs.get('nprobe', 3))
        # Reranking configuration
        self.rerank_k = int(kwargs.get('rerank_k', 16))
        # Training configuration
        self.train_size = int(kwargs.get('train_size', 250000))
        self.seed = int(kwargs.get('seed', 123))
        # Threading
        self.num_threads = int(kwargs.get('num_threads', max(1, (os.cpu_count() or 8))))
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        # Build FAISS index
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
        index.nprobe = self.nprobe
        try:
            index.use_precomputed_table = 1  # speed up PQ scanning
        except Exception:
            pass
        try:
            index.scan_table_threshold = 0  # always use LUT scanning
        except Exception:
            pass
        self.index: faiss.IndexIVFPQ = index

        # Store base vectors for optional reranking
        self._xb_chunks: List[np.ndarray] = []
        self._cum_counts: List[int] = [0]  # cumulative sizes to map global ids to chunks

        # For handling multiple add calls before training (rare)
        self._trained: bool = False

    def _choose_training_data(self, xb: np.ndarray) -> np.ndarray:
        n = xb.shape[0]
        if n <= 0:
            raise ValueError("No training data available.")
        rs = np.random.RandomState(self.seed)
        n_train = min(self.train_size, n)
        if n_train < n:
            idx = rs.choice(n, size=n_train, replace=False)
            xtrain = xb[idx]
        else:
            xtrain = xb
        return np.ascontiguousarray(xtrain, dtype=np.float32)

    def _append_chunk(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self._xb_chunks.append(xb)
        self._cum_counts.append(self._cum_counts[-1] + xb.shape[0])

    def _gather_vectors(self, idxs: np.ndarray) -> np.ndarray:
        out = np.empty((idxs.shape[0], self.dim), dtype=np.float32)
        # Handle negative indices (if any) by setting to zeros; distances will be set to inf later
        neg_mask = idxs < 0
        if np.any(neg_mask):
            out[neg_mask] = 0.0
        base = 0
        pos_mask = ~neg_mask
        idxs_pos = idxs[pos_mask]
        if idxs_pos.size > 0:
            start = 0
            for chunk, base in zip(self._xb_chunks, self._cum_counts[:-1]):
                end = base + chunk.shape[0]
                m = (idxs_pos >= base) & (idxs_pos < end)
                if not np.any(m):
                    continue
                local = idxs_pos[m] - base
                out[pos_mask][m] = chunk[local]
        return out

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        # Train if needed using the incoming batch
        if not self._trained:
            xtrain = self._choose_training_data(xb)
            self.index.train(xtrain)
            self._trained = True
        # Add to FAISS
        self.index.add(xb)
        # Store originals for reranking
        self._append_chunk(xb)

    def _exact_l2_rerank(self, xq: np.ndarray, I_cand: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        nq, R = I_cand.shape
        # Flatten and gather candidate vectors
        I_flat = I_cand.reshape(-1)
        V_flat = self._gather_vectors(I_flat)
        # Compute exact distances in manageable batches to control memory
        bytes_per = xq.dtype.itemsize
        max_bytes = 256 * 1024 * 1024  # 256 MB
        # bytes needed for (bs, R, dim) arrays
        denom = max(1, R * self.dim * bytes_per)
        bs = int(max(1, min(nq, max_bytes // denom)))
        D_final = np.empty((nq, k), dtype=np.float32)
        I_final = np.empty((nq, k), dtype=np.int64)

        for i0 in range(0, nq, bs):
            i1 = min(nq, i0 + bs)
            q_batch = xq[i0:i1]  # (bs, d)
            idx_batch = I_cand[i0:i1]  # (bs, R)
            V_batch = V_flat[i0 * R:i1 * R].reshape((i1 - i0, R, self.dim))  # (bs, R, d)

            # Compute squared L2 distances
            # dist = sum((v - q)^2)
            # Use broadcasting: (bs, R, d) - (bs, 1, d)
            diff = V_batch - q_batch[:, None, :]
            D_exact = np.einsum('brd,brd->br', diff, diff, optimize=True).astype(np.float32)

            # Set distances of invalid indices to +inf
            invalid = idx_batch < 0
            if np.any(invalid):
                D_exact[invalid] = np.inf

            # Select top-k per query
            if k < R:
                part = np.argpartition(D_exact, k - 1, axis=1)[:, :k]
                row_indices = np.arange(i1 - i0)[:, None]
                D_part = D_exact[row_indices, part]
                I_part = idx_batch[row_indices, part]
                order = np.argsort(D_part, axis=1)
                D_sorted = D_part[row_indices, order]
                I_sorted = I_part[row_indices, order]
                D_final[i0:i1] = D_sorted
                I_final[i0:i1] = I_sorted
            else:
                order = np.argsort(D_exact, axis=1)
                row_indices = np.arange(i1 - i0)[:, None]
                D_sorted = D_exact[row_indices, order][:, :k]
                I_sorted = idx_batch[row_indices, order][:, :k]
                D_final[i0:i1] = D_sorted
                I_final[i0:i1] = I_sorted

        return D_final, I_final

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        # Ensure the index is trained and has data
        if not self._trained:
            raise RuntimeError("Index must be trained before search. Call add() with training data first.")
        if self.index.ntotal == 0:
            raise RuntimeError("No vectors in the index. Call add() before search().")

        R = max(k, self.rerank_k) if self.rerank_k > 0 else k
        D_cand, I_cand = self.index.search(xq, R)

        if self.rerank_k > 0 and len(self._xb_chunks) > 0:
            D_final, I_final = self._exact_l2_rerank(xq, I_cand, k)
            return D_final.astype(np.float32, copy=False), I_final.astype(np.int64, copy=False)
        else:
            # Return approximate candidates directly
            if k < R:
                # Keep top-k from approximate results
                part = np.argpartition(D_cand, k - 1, axis=1)[:, :k]
                row = np.arange(D_cand.shape[0])[:, None]
                D_part = D_cand[row, part]
                I_part = I_cand[row, part]
                order = np.argsort(D_part, axis=1)
                D_sorted = D_part[row, order]
                I_sorted = I_part[row, order]
                return D_sorted.astype(np.float32, copy=False), I_sorted.astype(np.int64, copy=False)
            else:
                return D_cand.astype(np.float32, copy=False), I_cand.astype(np.int64, copy=False)
