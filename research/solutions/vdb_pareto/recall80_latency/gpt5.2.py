import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        nlist: int = 4096,
        nprobe: int = 4,
        m: int = 32,
        nbits: int = 8,
        opq: bool = True,
        train_size: int = 200_000,
        threads: int | None = None,
        precomputed_table: int = 1,
        kmeans_niter: int = 20,
        seed: int = 123,
        **kwargs,
    ):
        self.dim = int(dim)
        self.nlist = int(nlist)
        self.nprobe = int(nprobe)
        self.m = int(m)
        self.nbits = int(nbits)
        self.opq = bool(opq)
        self.train_size = int(train_size)
        self.threads = int(threads) if threads is not None else (os.cpu_count() or 1)
        self.precomputed_table = int(precomputed_table)
        self.kmeans_niter = int(kmeans_niter)
        self.seed = int(seed)

        self._use_faiss = faiss is not None
        self._xb_fallback = None

        if not self._use_faiss:
            return

        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        quantizer = faiss.IndexFlatL2(self.dim)

        ivf = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
        try:
            ivf.nprobe = self.nprobe
        except Exception:
            pass

        try:
            cp = ivf.cp
            cp.niter = self.kmeans_niter
            cp.seed = self.seed
            ivf.cp = cp
        except Exception:
            pass

        if self.opq:
            opq_mat = faiss.OPQMatrix(self.dim, self.m)
            try:
                opq_mat.niter = max(10, self.kmeans_niter)
                opq_mat.seed = self.seed
            except Exception:
                pass
            self.index = faiss.IndexPreTransform(opq_mat, ivf)
        else:
            self.index = ivf

        self._ivf = faiss.extract_index_ivf(self.index)

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return

        if xb.dtype != np.float32 or not xb.flags["C_CONTIGUOUS"]:
            xb = np.ascontiguousarray(xb, dtype=np.float32)

        if not self._use_faiss:
            if self._xb_fallback is None:
                self._xb_fallback = xb.copy()
            else:
                self._xb_fallback = np.vstack((self._xb_fallback, xb))
            return

        if not self.index.is_trained:
            N = xb.shape[0]
            ts = min(self.train_size, N)
            if ts < N:
                step = max(1, N // ts)
                train_x = xb[::step][:ts]
            else:
                train_x = xb
            if train_x.dtype != np.float32 or not train_x.flags["C_CONTIGUOUS"]:
                train_x = np.ascontiguousarray(train_x, dtype=np.float32)

            self.index.train(train_x)

            try:
                ivf = self._ivf
                if hasattr(ivf, "nprobe"):
                    ivf.nprobe = self.nprobe
            except Exception:
                pass

            try:
                ivf2 = faiss.extract_index_ivf(self.index)
                if isinstance(ivf2, faiss.IndexIVFPQ):
                    ivfpq = ivf2
                    try:
                        ivfpq.use_precomputed_table = self.precomputed_table
                    except Exception:
                        pass
                    try:
                        ivfpq.precompute_table()
                    except Exception:
                        pass
            except Exception:
                pass

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            nq = 0 if xq is None else int(xq.shape[0])
            return (
                np.empty((nq, 0), dtype=np.float32),
                np.empty((nq, 0), dtype=np.int64),
            )

        if xq is None or xq.size == 0:
            return (
                np.empty((0, k), dtype=np.float32),
                np.empty((0, k), dtype=np.int64),
            )

        if xq.dtype != np.float32 or not xq.flags["C_CONTIGUOUS"]:
            xq = np.ascontiguousarray(xq, dtype=np.float32)

        nq = int(xq.shape[0])

        if not self._use_faiss:
            if self._xb_fallback is None or self._xb_fallback.size == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            xb = self._xb_fallback
            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
            sims = xq @ xb.T
            dists = xq_norm + xb_norm - 2.0 * sims  # squared L2
            idx = np.argpartition(dists, kth=min(k - 1, dists.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dd = dists[row, idx]
            order = np.argsort(dd, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dd[row, order].astype(np.float32, copy=False)
            if I.shape[1] < k:
                pad = k - I.shape[1]
                I = np.hstack([I, np.full((nq, pad), -1, dtype=np.int64)])
                D = np.hstack([D, np.full((nq, pad), np.inf, dtype=np.float32)])
            return D, I

        if self.index.ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I