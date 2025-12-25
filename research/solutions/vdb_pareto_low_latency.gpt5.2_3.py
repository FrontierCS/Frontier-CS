import os
from typing import Tuple, Optional, List

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs,
    ):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", kwargs.get("ef_search", 48)))
        self.train_size = int(kwargs.get("train_size", 150_000))
        self.niter = int(kwargs.get("niter", 12))
        self.threads = kwargs.get("threads", None)

        if self.threads is None:
            self.threads = min(8, os.cpu_count() or 1)
        self.threads = int(self.threads)

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.threads)
            except Exception:
                pass

        self._index = None
        self._ntotal = 0
        self._pending: List[np.ndarray] = []
        self._pending_rows = 0

    def _as_float32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _build_faiss_index(self, xb_sample: np.ndarray):
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        try:
            index.cp.niter = self.niter
            index.cp.max_points_per_centroid = 256
            index.cp.seed = 12345
        except Exception:
            pass
        index.nprobe = self.nprobe
        return index

    def _train_if_needed(self, xb: np.ndarray) -> None:
        if self._index is not None:
            return

        if faiss is None:
            self._index = ("numpy", xb.copy())
            self._ntotal = xb.shape[0]
            return

        n = xb.shape[0]
        if n < max(256, self.nlist):
            self._index = faiss.IndexFlatL2(self.dim)
            self._index.add(xb)
            self._ntotal = int(self._index.ntotal)
            return

        self._index = self._build_faiss_index(xb)

        ts = min(self.train_size, n)
        if ts < self.nlist:
            ts = self.nlist

        if ts >= n:
            xtrain = xb
        else:
            step = max(1, n // ts)
            idx = np.arange(0, n, step, dtype=np.int64)[:ts]
            xtrain = xb[idx]

        if not self._index.is_trained:
            self._index.train(xtrain)

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_float32_contig(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        if self._index is None and faiss is not None:
            self._pending.append(xb)
            self._pending_rows += xb.shape[0]
            min_rows = max(self.nlist * 32, self.nlist + 1, 50000)
            if self._pending_rows < min_rows:
                return
            xb_all = np.vstack(self._pending) if len(self._pending) > 1 else self._pending[0]
            self._pending.clear()
            self._pending_rows = 0
            xb = xb_all

        self._train_if_needed(xb)

        if faiss is None:
            # numpy fallback
            if isinstance(self._index, tuple) and self._index[0] == "numpy":
                self._index = ("numpy", np.vstack([self._index[1], xb]))
            else:
                self._index = ("numpy", xb.copy())
            self._ntotal = self._index[1].shape[0]
            return

        if isinstance(self._index, tuple):
            # should not happen in faiss-present path, but keep safe
            self._index = faiss.IndexFlatL2(self.dim)
            self._index.add(self._index[1])
            self._index.add(xb)
        else:
            if not self._index.is_trained:
                self._index.train(xb[: min(xb.shape[0], max(self.nlist * 32, 50000))])
            self._index.add(xb)

        self._ntotal = int(self._index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            raise ValueError("k must be >= 1")
        xq = self._as_float32_contig(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        if self._index is None:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        if faiss is None or (isinstance(self._index, tuple) and self._index[0] == "numpy"):
            xb = self._index[1]
            nq = xq.shape[0]
            N = xb.shape[0]
            kk = min(k, N)
            if kk == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            xq2 = (xq * xq).sum(axis=1, keepdims=True)
            xb2 = (xb * xb).sum(axis=1)[None, :]
            block = 20000
            best_D = np.full((nq, kk), np.inf, dtype=np.float32)
            best_I = np.full((nq, kk), -1, dtype=np.int64)

            for start in range(0, N, block):
                end = min(N, start + block)
                xb_blk = xb[start:end]
                d2 = xq2 + xb2[:, start:end] - 2.0 * (xq @ xb_blk.T)
                if kk == 1:
                    ii = np.argmin(d2, axis=1)
                    dd = d2[np.arange(nq), ii]
                    mask = dd < best_D[:, 0]
                    best_D[mask, 0] = dd[mask]
                    best_I[mask, 0] = ii[mask] + start
                else:
                    ii = np.argpartition(d2, kk - 1, axis=1)[:, :kk]
                    dd = d2[np.arange(nq)[:, None], ii]
                    merged_D = np.concatenate([best_D, dd.astype(np.float32, copy=False)], axis=1)
                    merged_I = np.concatenate([best_I, (ii + start).astype(np.int64, copy=False)], axis=1)
                    sel = np.argpartition(merged_D, kk - 1, axis=1)[:, :kk]
                    best_D = merged_D[np.arange(nq)[:, None], sel]
                    best_I = merged_I[np.arange(nq)[:, None], sel]

            order = np.argsort(best_D, axis=1)
            best_D = best_D[np.arange(nq)[:, None], order]
            best_I = best_I[np.arange(nq)[:, None], order]

            if kk < k:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                D[:, :kk] = best_D
                I[:, :kk] = best_I
                return D, I
            return best_D.astype(np.float32, copy=False), best_I.astype(np.int64, copy=False)

        if self._pending:
            xb_all = np.vstack(self._pending) if len(self._pending) > 1 else self._pending[0]
            self._pending.clear()
            self._pending_rows = 0
            self.add(xb_all)

        idx = self._index
        try:
            idx.nprobe = self.nprobe
        except Exception:
            pass

        nt = int(idx.ntotal)
        nq = xq.shape[0]
        kk = min(k, nt) if nt > 0 else 0

        if kk == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        D, I = idx.search(xq, kk)

        if kk < k:
            D2 = np.full((nq, k), np.inf, dtype=np.float32)
            I2 = np.full((nq, k), -1, dtype=np.int64)
            D2[:, :kk] = D
            I2[:, :kk] = I
            return D2, I2

        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)