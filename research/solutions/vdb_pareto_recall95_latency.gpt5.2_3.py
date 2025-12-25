import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 120))
        self.ef_search = int(kwargs.get("ef_search", 64))
        self.threads = int(kwargs.get("threads", max(1, (os.cpu_count() or 8))))

        self._ntotal = 0

        if faiss is None:
            self._xb = None
            return

        faiss.omp_set_num_threads(self.threads)

        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        try:
            self.index.hnsw.search_bounded_queue = True
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        if faiss is None:
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            self._ntotal = int(self._xb.shape[0])
            return

        self.index.add(xb)
        self._ntotal = int(self.index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        nq = int(xq.shape[0])
        if self._ntotal <= 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        if faiss is None:
            xb = self._xb
            if xb is None:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            xb_norm = (xb * xb).sum(axis=1, dtype=np.float32)
            xq_norm = (xq * xq).sum(axis=1, dtype=np.float32)

            k_eff = min(k, xb.shape[0])
            D_out = np.empty((nq, k), dtype=np.float32)
            I_out = np.empty((nq, k), dtype=np.int64)

            bs = 256
            for i0 in range(0, nq, bs):
                i1 = min(nq, i0 + bs)
                q = xq[i0:i1]
                prod = q @ xb.T
                d2 = xq_norm[i0:i1, None] + xb_norm[None, :] - 2.0 * prod
                idx = np.argpartition(d2, k_eff - 1, axis=1)[:, :k_eff]
                d2_sel = d2[np.arange(i1 - i0)[:, None], idx]
                order = np.argsort(d2_sel, axis=1)
                idx = idx[np.arange(i1 - i0)[:, None], order]
                d2_sel = d2_sel[np.arange(i1 - i0)[:, None], order]

                if k_eff < k:
                    I_out[i0:i1, :k_eff] = idx.astype(np.int64, copy=False)
                    D_out[i0:i1, :k_eff] = d2_sel.astype(np.float32, copy=False)
                    I_out[i0:i1, k_eff:] = -1
                    D_out[i0:i1, k_eff:] = np.inf
                else:
                    I_out[i0:i1, :] = idx.astype(np.int64, copy=False)
                    D_out[i0:i1, :] = d2_sel.astype(np.float32, copy=False)

            return D_out, I_out

        self.index.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I