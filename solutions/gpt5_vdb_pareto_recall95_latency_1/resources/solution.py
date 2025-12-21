import os
import math
import numpy as np
from typing import Tuple

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self._index = None
        self._is_trained = False
        self._added = 0

        self._cfg_nlist = kwargs.get("nlist", None)
        self._cfg_nprobe = kwargs.get("nprobe", 128)
        self._cfg_train_size = kwargs.get("train_size", None)
        self._seed = kwargs.get("seed", 123)

        if faiss is not None:
            nt = kwargs.get("num_threads", None)
            if nt is None:
                cpu_cnt = os.cpu_count() or 8
                nt = max(1, cpu_cnt)
            try:
                faiss.omp_set_num_threads(nt)
            except Exception:
                pass

    def _choose_nlist(self, N: int) -> int:
        if self._cfg_nlist is not None:
            nlist = int(self._cfg_nlist)
        else:
            if N >= 1_000_000:
                nlist = 8192
            elif N >= 200_000:
                nlist = 4096
            elif N >= 50_000:
                nlist = 2048
            elif N >= 10_000:
                nlist = 1024
            else:
                est = max(32, int(4 * math.sqrt(max(N, 1))))
                # round to power of two for small N
                p = 1 << (est - 1).bit_length()
                nlist = max(32, min(p, 1024))
        nlist = max(1, min(nlist, N))
        return nlist

    def _choose_train_size(self, N: int, nlist: int) -> int:
        if self._cfg_train_size is not None:
            return int(min(max(self._cfg_train_size, nlist), N))
        if N >= 1_000_000:
            ts = 256_000
        elif N >= 200_000:
            ts = 128_000
        else:
            ts = min(64_000, N)
        ts = max(nlist, min(ts, N))
        return ts

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.asarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dtype float32")

        N = xb.shape[0]

        if faiss is None:
            # Fallback: store for brute-force search
            if not hasattr(self, "_xb"):
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            self._added += N
            return

        if self._index is None:
            nlist = self._choose_nlist(N)
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, faiss.METRIC_L2)

            # Train with a representative sample
            train_sz = self._choose_train_size(N, nlist)
            if train_sz < N:
                rng = np.random.default_rng(self._seed)
                idx = rng.choice(N, size=train_sz, replace=False)
                xtrain = xb[idx]
            else:
                xtrain = xb

            if not index.is_trained:
                index.train(xtrain)

            nprobe = int(self._cfg_nprobe)
            index.nprobe = max(1, min(nprobe, nlist))
            self._index = index
            self._is_trained = True

        self._index.add(xb)
        self._added += N

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            xq = np.asarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dtype float32")
        if k <= 0:
            raise ValueError("k must be positive")

        if faiss is not None and self._index is not None and self._added > 0:
            D, I = self._index.search(xq, k)
            return D, I

        # Fallback brute-force search if faiss not available or index not built
        if not hasattr(self, "_xb") or self._added == 0:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xb = self._xb
        nq = xq.shape[0]
        N = xb.shape[0]
        k = min(k, N)

        bs = 2048
        all_D = np.empty((nq, k), dtype=np.float32)
        all_I = np.empty((nq, k), dtype=np.int64)
        for i0 in range(0, nq, bs):
            i1 = min(i0 + bs, nq)
            q = xq[i0:i1]
            # Compute squared L2 distances using (a - b)^2 = a^2 + b^2 - 2ab
            q_norms = np.sum(q * q, axis=1, keepdims=True)
            xb_norms = np.sum(xb * xb, axis=1, keepdims=True).T
            dots = q @ xb.T
            dists = q_norms + xb_norms - 2.0 * dots
            idx = np.argpartition(dists, kth=k - 1, axis=1)[:, :k]
            part = dists[np.arange(i1 - i0)[:, None], idx]
            ord = np.argsort(part, axis=1)
            final_idx = idx[np.arange(i1 - i0)[:, None], ord]
            final_d = part[np.arange(i1 - i0)[:, None], ord]
            all_D[i0:i1] = final_d.astype(np.float32, copy=False)
            all_I[i0:i1] = final_idx.astype(np.int64, copy=False)

        return all_D, all_I
