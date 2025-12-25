import os
import gc
import numpy as np
from typing import Tuple, Optional

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


def _as_float32_contig(x: np.ndarray) -> np.ndarray:
    if x is None:
        return x
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    if not x.flags["C_CONTIGUOUS"]:
        x = np.ascontiguousarray(x)
    return x


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.n_threads = int(kwargs.get("n_threads", min(8, os.cpu_count() or 1)))
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 96))

        self.m = int(kwargs.get("m", 64))
        self.nbits = int(kwargs.get("nbits", 8))

        self.k_factor = int(kwargs.get("k_factor", 256))

        self.train_size = kwargs.get("train_size", None)  # can be None; chosen on first add

        self._use_faiss = faiss is not None
        self._xb_fallback: Optional[np.ndarray] = None

        self._index = None
        self._base = None
        self._refine = None

        if self._use_faiss:
            faiss.omp_set_num_threads(self.n_threads)
            quantizer = faiss.IndexFlatL2(self.dim)
            base = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
            refine = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexRefineFlat(base, refine)
            index.k_factor = self.k_factor

            base.nprobe = self.nprobe

            self._base = base
            self._refine = refine
            self._index = index

    def add(self, xb: np.ndarray) -> None:
        xb = _as_float32_contig(xb)
        if xb is None or xb.size == 0:
            return
        if xb.shape[1] != self.dim:
            raise ValueError(f"xb dim mismatch: expected {self.dim}, got {xb.shape[1]}")

        if not self._use_faiss:
            if self._xb_fallback is None:
                self._xb_fallback = xb.copy()
            else:
                self._xb_fallback = np.vstack([self._xb_fallback, xb])
            return

        assert self._base is not None and self._index is not None

        if not self._base.is_trained:
            n = xb.shape[0]
            if self.train_size is None:
                self.train_size = int(min(n, max(200000, min(500000, 50 * self.nlist))))
            ts = int(min(self.train_size, n))

            if ts < self.nlist:
                ts = min(n, self.nlist)

            if ts == n:
                xtrain = xb
            else:
                rng = np.random.default_rng(12345)
                idx = rng.choice(n, size=ts, replace=False)
                xtrain = xb[idx]

            xtrain = _as_float32_contig(xtrain)
            self._index.train(xtrain)
            if xtrain is not xb:
                del xtrain
                gc.collect()

        self._base.nprobe = self.nprobe
        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            nq = int(xq.shape[0])
            return (
                np.empty((nq, 0), dtype=np.float32),
                np.empty((nq, 0), dtype=np.int64),
            )

        xq = _as_float32_contig(xq)
        if xq is None or xq.size == 0:
            return (
                np.empty((0, k), dtype=np.float32),
                np.empty((0, k), dtype=np.int64),
            )
        if xq.shape[1] != self.dim:
            raise ValueError(f"xq dim mismatch: expected {self.dim}, got {xq.shape[1]}")

        nq = xq.shape[0]

        if not self._use_faiss:
            xb = self._xb_fallback
            if xb is None or xb.shape[0] == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            xb = _as_float32_contig(xb)
            xb_norm = (xb * xb).sum(axis=1).astype(np.float32, copy=False)

            D_best = np.full((nq, k), np.inf, dtype=np.float32)
            I_best = np.full((nq, k), -1, dtype=np.int64)

            xq_norm = (xq * xq).sum(axis=1).astype(np.float32, copy=False)

            block = 50000
            for i0 in range(0, xb.shape[0], block):
                i1 = min(i0 + block, xb.shape[0])
                xb_blk = xb[i0:i1]
                dot = xq @ xb_blk.T
                d2 = (xq_norm[:, None] + xb_norm[i0:i1][None, :] - 2.0 * dot).astype(np.float32, copy=False)

                kk = min(k, i1 - i0)
                idx_part = np.argpartition(d2, kk - 1, axis=1)[:, :kk]
                d_part = np.take_along_axis(d2, idx_part, axis=1)

                idx_global = (idx_part + i0).astype(np.int64, copy=False)

                all_d = np.concatenate([D_best, d_part], axis=1)
                all_i = np.concatenate([I_best, idx_global], axis=1)

                sel = np.argpartition(all_d, k - 1, axis=1)[:, :k]
                D_best = np.take_along_axis(all_d, sel, axis=1)
                I_best = np.take_along_axis(all_i, sel, axis=1)

            order = np.argsort(D_best, axis=1)
            D_best = np.take_along_axis(D_best, order, axis=1).astype(np.float32, copy=False)
            I_best = np.take_along_axis(I_best, order, axis=1).astype(np.int64, copy=False)
            return D_best, I_best

        assert self._index is not None and self._base is not None

        if self._index.ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        self._base.nprobe = self.nprobe
        self._index.k_factor = self.k_factor

        D, I = self._index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        if D.shape[1] != k:
            D2 = np.full((nq, k), np.inf, dtype=np.float32)
            I2 = np.full((nq, k), -1, dtype=np.int64)
            kk = min(k, D.shape[1])
            D2[:, :kk] = D[:, :kk]
            I2[:, :kk] = I[:, :kk]
            return D2, I2

        return D, I