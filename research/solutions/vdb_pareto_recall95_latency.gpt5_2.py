import numpy as np
from typing import Tuple
import os

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", kwargs.get("efConstruction", 200)))
        self.ef_search = int(kwargs.get("ef_search", kwargs.get("efSearch", 128)))
        self.num_threads = kwargs.get("num_threads", os.cpu_count() or 1)

        self.index = None
        self.ntotal = 0

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            # Set construction/search parameters
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search
        else:
            # Fallback storage for extremely small datasets if faiss is unavailable (not intended for SIFT1M)
            self._xb = None

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if faiss is not None and self.index is not None:
            self.index.add(xb)
            self.ntotal = self.index.ntotal
        else:
            # naive fallback (not for large datasets)
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack((self._xb, xb))
            self.ntotal = self._xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if faiss is not None and self.index is not None:
            # Ensure efSearch is set for each search (in case user modified parameter after init)
            self.index.hnsw.efSearch = self.ef_search
            D, I = self.index.search(xq, k)
            # Ensure dtypes
            if D.dtype != np.float32:
                D = D.astype(np.float32, copy=False)
            if I.dtype != np.int64:
                I = I.astype(np.int64, copy=False)
            return D, I
        else:
            # naive fallback (not for large datasets)
            if self._xb is None or self.ntotal == 0:
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

            xb = self._xb
            # Compute squared L2 distances in blocks to reduce memory
            nq = xq.shape[0]
            N = xb.shape[0]
            D_out = np.empty((nq, k), dtype=np.float32)
            I_out = np.empty((nq, k), dtype=np.int64)

            block = 8192
            xb_norms = np.sum(xb.astype(np.float32) ** 2, axis=1)

            for i0 in range(0, nq, block):
                i1 = min(i0 + block, nq)
                Q = xq[i0:i1].astype(np.float32)
                q_norms = np.sum(Q ** 2, axis=1, keepdims=True)
                # Compute -2*Q*X^T
                dots = Q @ xb.T
                dists = q_norms + xb_norms[None, :] - 2.0 * dots
                # Argpartition top-k
                idx_part = np.argpartition(dists, kth=range(k), axis=1)[:, :k]
                row_idx = np.arange(i1 - i0)[:, None]
                part_d = dists[row_idx, idx_part]
                order = np.argsort(part_d, axis=1)
                final_idx = idx_part[row_idx, order]
                final_d = part_d[row_idx, order]
                D_out[i0:i1] = final_d.astype(np.float32, copy=False)
                I_out[i0:i1] = final_idx.astype(np.int64, copy=False)

            return D_out, I_out