import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 512))

        self.rerank = bool(kwargs.get("rerank", True))
        self.rerank_k = int(kwargs.get("rerank_k", 128))
        self.rerank_batch_size = int(kwargs.get("rerank_batch_size", 256))

        threads = kwargs.get("threads", None)
        if threads is None:
            threads = os.cpu_count() or 1
        self.threads = int(max(1, threads))

        self._xb_ref: Optional[np.ndarray] = None
        self._xb_chunks = []
        self._xb_final: Optional[np.ndarray] = None
        self._ntotal = 0

        if faiss is None:
            self.index = None
        else:
            faiss.omp_set_num_threads(self.threads)
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if self.rerank:
            if self._ntotal == 0 and xb.flags["C_CONTIGUOUS"] and xb.dtype == np.float32:
                self._xb_ref = xb
            else:
                self._xb_chunks.append(xb)

        if faiss is None:
            if self._xb_final is None:
                self._xb_final = xb
            else:
                self._xb_final = np.vstack([self._xb_final, xb])
        else:
            faiss.omp_set_num_threads(self.threads)
            self.index.add(xb)

        self._ntotal += xb.shape[0]

    def _ensure_xb(self) -> np.ndarray:
        if self._xb_final is not None:
            return self._xb_final
        if self._xb_ref is not None and not self._xb_chunks:
            self._xb_final = self._xb_ref
            return self._xb_final
        if self._xb_ref is None and not self._xb_chunks:
            raise RuntimeError("No vectors added")
        if self._xb_ref is None:
            self._xb_final = np.vstack(self._xb_chunks)
        else:
            self._xb_final = np.vstack([self._xb_ref] + self._xb_chunks)
        self._xb_chunks.clear()
        self._xb_ref = None
        return self._xb_final

    def _rerank_exact(self, xq: np.ndarray, candI: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xb = self._ensure_xb()

        nq, k2 = candI.shape
        D_out = np.empty((nq, k), dtype=np.float32)
        I_out = np.empty((nq, k), dtype=np.int64)

        bs = int(max(1, self.rerank_batch_size))
        dim = self.dim

        for i0 in range(0, nq, bs):
            i1 = min(nq, i0 + bs)
            q = xq[i0:i1]
            idx = candI[i0:i1].astype(np.int64, copy=False)

            valid = idx >= 0
            idx_safe = np.where(valid, idx, 0)

            flat = idx_safe.reshape(-1)
            vecs = xb[flat].reshape(i1 - i0, k2, dim)

            qnorm = np.sum(q * q, axis=1, dtype=np.float32)[:, None]
            xnorm = np.sum(vecs * vecs, axis=2, dtype=np.float32)
            dot = np.sum(vecs * q[:, None, :], axis=2, dtype=np.float32)
            dist = qnorm + xnorm - (2.0 * dot)

            if not np.all(valid):
                dist = np.where(valid, dist, np.float32(np.inf))

            if k == 1:
                j = np.argmin(dist, axis=1)
                I_out[i0:i1, 0] = idx[np.arange(i1 - i0), j]
                D_out[i0:i1, 0] = dist[np.arange(i1 - i0), j].astype(np.float32, copy=False)
            else:
                part = np.argpartition(dist, kth=k - 1, axis=1)[:, :k]
                part_dist = np.take_along_axis(dist, part, axis=1)
                order = np.argsort(part_dist, axis=1)
                top = np.take_along_axis(part, order, axis=1)
                top_dist = np.take_along_axis(dist, top, axis=1)

                I_out[i0:i1] = np.take_along_axis(idx, top, axis=1)
                D_out[i0:i1] = top_dist.astype(np.float32, copy=False)

        bad = I_out < 0
        if np.any(bad):
            I_out[bad] = 0
            D_out[bad] = np.float32(np.inf)

        return D_out, I_out

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if faiss is None:
            xb = self._ensure_xb()
            qnorm = np.sum(xq * xq, axis=1, dtype=np.float32)[:, None]
            xnorm = np.sum(xb * xb, axis=1, dtype=np.float32)[None, :]
            dots = xq @ xb.T
            dist = qnorm + xnorm - 2.0 * dots.astype(np.float32, copy=False)

            idx = np.argpartition(dist, kth=k - 1, axis=1)[:, :k]
            part_dist = np.take_along_axis(dist, idx, axis=1)
            order = np.argsort(part_dist, axis=1)
            I = np.take_along_axis(idx, order, axis=1).astype(np.int64, copy=False)
            D = np.take_along_axis(dist, I, axis=1).astype(np.float32, copy=False)
            return D, I

        faiss.omp_set_num_threads(self.threads)

        if not self.rerank:
            self.index.hnsw.efSearch = max(self.ef_search, k)
            D, I = self.index.search(xq, k)
            return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)

        k2 = max(k, int(self.rerank_k))
        self.index.hnsw.efSearch = max(self.ef_search, k2)
        _, candI = self.index.search(xq, k2)
        candI = candI.astype(np.int64, copy=False)

        return self._rerank_exact(xq, candI, k)