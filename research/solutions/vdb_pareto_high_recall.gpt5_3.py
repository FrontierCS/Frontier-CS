import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        nlist: Optional[int] = None,
        nprobe: int = 224,
        train_size: int = 250000,
        use_hnsw_quantizer: bool = False,
        hnsw_m: int = 32,
        hnsw_ef_construction: int = 200,
        hnsw_ef_search: int = 128,
        threads: Optional[int] = None,
        seed: int = 123,
        **kwargs,
    ):
        self.dim = int(dim)
        self._index = None
        self._is_trained = False
        self._xb_count = 0

        self._user_nlist = nlist
        self.nprobe = int(nprobe)
        self.train_size = int(train_size)
        self.use_hnsw_quantizer = bool(use_hnsw_quantizer)
        self.hnsw_m = int(hnsw_m)
        self.hnsw_ef_construction = int(hnsw_ef_construction)
        self.hnsw_ef_search = int(hnsw_ef_search)
        self.seed = int(seed)

        # Set FAISS threads
        if faiss is not None:
            if threads is None:
                threads_env = os.environ.get("FAISS_NT")
                if threads_env is not None:
                    try:
                        threads = int(threads_env)
                    except Exception:
                        threads = None
                if threads is None:
                    threads = os.cpu_count() or 8
            try:
                faiss.omp_set_num_threads(int(max(1, threads)))
            except Exception:
                pass

        # For fallback if faiss is unavailable (not expected)
        self._xb_fallback = None

    def _build_index(self, N_hint: int):
        if faiss is None:
            self._xb_fallback = np.empty((0, self.dim), dtype=np.float32)
            return

        # Determine nlist
        if self._user_nlist is not None:
            nlist = int(self._user_nlist)
        else:
            # Heuristic: target ~64 vectors per list
            nlist = max(4096, min(16384, int(max(1, round(N_hint / 64)))))
            # Round to nearest power of 2 among common choices
            candidates = np.array([4096, 8192, 16384, 32768], dtype=int)
            nlist = int(candidates[np.argmin(np.abs(candidates - nlist))])
            nlist = max(4096, min(16384, nlist))

        self._nlist = nlist

        # Build quantizer
        if self.use_hnsw_quantizer:
            quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
            quantizer.hnsw.efConstruction = self.hnsw_ef_construction
            quantizer.hnsw.efSearch = self.hnsw_ef_search
        else:
            quantizer = faiss.IndexFlatL2(self.dim)

        index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, faiss.METRIC_L2)
        index.nprobe = int(self.nprobe)
        self._index = index

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dtype float32")

        N_chunk = xb.shape[0]
        if self._index is None:
            self._build_index(N_chunk)

        if faiss is None:
            # Fallback brute-force storage (slow)
            if self._xb_fallback is None:
                self._xb_fallback = xb.copy()
            else:
                self._xb_fallback = np.vstack([self._xb_fallback, xb])
            self._xb_count += N_chunk
            return

        if not self._is_trained:
            # Train with a sample from the current chunk
            rs = np.random.RandomState(self.seed)
            train_n = min(self.train_size, N_chunk)
            if train_n < self._nlist:
                # if extremely small chunk, ensure enough training data
                train_n = min(N_chunk, max(self._nlist, self.train_size // 2))
            if train_n >= N_chunk:
                xtrain = xb
            else:
                idx = rs.choice(N_chunk, size=train_n, replace=False)
                xtrain = xb[idx]

            self._index.train(np.ascontiguousarray(xtrain, dtype=np.float32))
            # For HNSW quantizer, increase efSearch after centroids are added
            if self.use_hnsw_quantizer and isinstance(self._index.quantizer, faiss.IndexHNSWFlat):
                try:
                    self._index.quantizer.hnsw.efSearch = self.hnsw_ef_search
                except Exception:
                    pass
            self._is_trained = True

        self._index.add(np.ascontiguousarray(xb, dtype=np.float32))
        self._xb_count += N_chunk

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dtype float32")

        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        if faiss is None:
            # Fallback brute-force search (very slow; not intended for large N)
            if self._xb_fallback is None or self._xb_fallback.shape[0] == 0:
                N = 0
            else:
                N = self._xb_fallback.shape[0]
            if N == 0:
                D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
                I = np.full((xq.shape[0], k), -1, dtype=np.int64)
                return D, I

            xb = self._xb_fallback
            # Compute squared L2 distances
            # (xq - xb)^2 = ||xq||^2 + ||xb||^2 - 2 xq xb^T
            xq_norm = (xq ** 2).sum(axis=1, keepdims=True)
            xb_norm = (xb ** 2).sum(axis=1, keepdims=True).T
            dots = xq @ xb.T
            distances = xq_norm + xb_norm - 2.0 * dots

            k_eff = min(k, N)
            idx_part = np.argpartition(distances, kth=k_eff - 1, axis=1)[:, :k_eff]
            row_idx = np.arange(xq.shape[0])[:, None]
            part_dist = distances[row_idx, idx_part]
            order = np.argsort(part_dist, axis=1)
            sorted_idx = idx_part[row_idx, order]

            D = distances[row_idx, sorted_idx]
            I = sorted_idx.astype(np.int64)
            if k_eff < k:
                pad = k - k_eff
                D = np.concatenate([D, np.full((xq.shape[0], pad), np.inf, dtype=np.float32)], axis=1)
                I = np.concatenate([I, np.full((xq.shape[0], pad), -1, dtype=np.int64)], axis=1)
            return D.astype(np.float32), I.astype(np.int64)

        if self._index is None or not self._is_trained:
            # No data added or index not trained; return empty results
            D = np.full((xq.shape[0], k), np.inf, dtype=np.float32)
            I = np.full((xq.shape[0], k), -1, dtype=np.int64)
            return D, I

        # Ensure nprobe set
        try:
            self._index.nprobe = int(self.nprobe)
        except Exception:
            pass

        D, I = self._index.search(np.ascontiguousarray(xq, dtype=np.float32), k)
        # Ensure types
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I