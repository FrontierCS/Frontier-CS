import os
import math
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.n_threads = int(kwargs.get("n_threads", os.cpu_count() or 1))
        self.metric = "l2"

        self.nlist: Optional[int] = kwargs.get("nlist", None)
        self.nprobe: Optional[int] = kwargs.get("nprobe", None)

        self.train_size: Optional[int] = kwargs.get("train_size", None)
        self.autotune: bool = bool(kwargs.get("autotune", True))
        self.autotune_target_recall: float = float(kwargs.get("autotune_target_recall", 0.97))
        self.autotune_n_val: int = int(kwargs.get("autotune_n_val", 200))
        self.autotune_k: int = int(kwargs.get("autotune_k", 10))

        self._index = None
        self._trained = False
        self._ntotal = 0

        if faiss is not None:
            faiss.omp_set_num_threads(self.n_threads)

    def _as_f32(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _choose_nlist(self, N: int) -> int:
        if self.nlist is not None:
            nlist = int(self.nlist)
        else:
            target = int(4.0 * math.sqrt(max(N, 1)))
            if target < 1024 and N >= 200_000:
                target = 1024
            nlist = 1
            while nlist < target:
                nlist <<= 1
            if nlist > 16384:
                nlist = 16384

        if N < 100:
            return max(1, min(nlist, N))

        max_nlist = max(1, min(nlist, max(1, N // 39)))
        if max_nlist < nlist:
            n = 1
            while (n << 1) <= max_nlist:
                n <<= 1
            nlist = n
        return max(1, nlist)

    def _choose_nprobe(self, nlist: int) -> int:
        if self.nprobe is not None:
            nprobe = int(self.nprobe)
        else:
            nprobe = nlist // 100  # 4096->40
            if nprobe < 8:
                nprobe = 8
            if nprobe > 128:
                nprobe = 128
        if nprobe > nlist:
            nprobe = nlist
        if nprobe < 1:
            nprobe = 1
        return nprobe

    def _choose_train_size(self, N: int, nlist: int) -> int:
        if self.train_size is not None:
            ts = int(self.train_size)
        else:
            ts = max(100_000, nlist * 50)
        ts = min(N, ts)
        min_needed = min(N, max(nlist * 20, nlist + 1))
        if ts < min_needed:
            ts = min_needed
        return ts

    def _build_index(self, nlist: int, nprobe: int):
        if faiss is None:
            self._index = None
            return

        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, faiss.METRIC_L2)
        try:
            index.cp.niter = 20
            index.cp.max_points_per_centroid = 256
        except Exception:
            pass
        index.nprobe = nprobe
        self._index = index

    def _sample_train(self, xb: np.ndarray, train_size: int) -> np.ndarray:
        N = xb.shape[0]
        if train_size >= N:
            return xb
        rng = np.random.default_rng(12345)
        idx = rng.choice(N, size=train_size, replace=False)
        return xb[idx]

    @staticmethod
    def _first_not_self(I: np.ndarray, self_ids: np.ndarray) -> np.ndarray:
        # I: (nq, k), self_ids: (nq,)
        nq, kk = I.shape
        out = np.empty(nq, dtype=np.int64)
        for i in range(nq):
            sid = int(self_ids[i])
            row = I[i]
            chosen = -1
            for j in range(kk):
                v = int(row[j])
                if v != sid and v >= 0:
                    chosen = v
                    break
            out[i] = chosen
        return out

    def _autotune_nprobe(self, xb: np.ndarray):
        if not self.autotune or faiss is None or self._index is None:
            return

        N = xb.shape[0]
        n_val = min(self.autotune_n_val, N)
        if n_val < 50:
            return

        rng = np.random.default_rng(123)
        q_ids = rng.choice(N, size=n_val, replace=False).astype(np.int64)
        xval = xb[q_ids]
        xval = self._as_f32(xval)

        k = max(2, int(self.autotune_k))
        try:
            exact = faiss.IndexFlatL2(self.dim)
            exact.add(xb)
            _, Igt = exact.search(xval, k)
        finally:
            try:
                del exact
            except Exception:
                pass

        gt_best = self._first_not_self(Igt, q_ids)

        nlist = int(self._index.nlist)
        candidates = []
        for p in (8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64, 80, 96, 128, 160, 192, 256, 320, 384, 512):
            if p <= nlist:
                candidates.append(p)
        if not candidates:
            candidates = [min(1, nlist)]
        candidates = sorted(set(candidates))

        best_p = int(self._index.nprobe)
        for p in candidates:
            self._index.nprobe = int(p)
            _, Iap = self._index.search(xval, k)
            ap_best = self._first_not_self(Iap, q_ids)
            valid = (gt_best >= 0)
            if not np.any(valid):
                continue
            recall = float(np.mean(ap_best[valid] == gt_best[valid]))
            if recall >= self.autotune_target_recall:
                best_p = int(p)
                break

        self._index.nprobe = int(best_p)
        self.nprobe = int(best_p)

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_f32(xb)
        N = int(xb.shape[0])
        if N == 0:
            return
        if xb.shape[1] != self.dim:
            raise ValueError(f"xb dim mismatch: xb.shape[1]={xb.shape[1]} vs dim={self.dim}")

        if faiss is None:
            if not hasattr(self, "_xb") or self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])
            self._ntotal = int(self._xb.shape[0])
            return

        if self._index is None:
            nlist = self._choose_nlist(N)
            nprobe = self._choose_nprobe(nlist)
            self.nlist = nlist
            self.nprobe = nprobe
            self._build_index(nlist, nprobe)

        if self._index is None:
            return

        if not self._trained:
            train_size = self._choose_train_size(N, int(self._index.nlist))
            xt = self._sample_train(xb, train_size)
            xt = self._as_f32(xt)
            self._index.train(xt)
            self._trained = True

        self._index.add(xb)
        self._ntotal += N

        self._autotune_nprobe(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            nq = int(xq.shape[0])
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        xq = self._as_f32(xq)
        nq = int(xq.shape[0])
        if nq == 0:
            return np.empty((0, k), dtype=np.float32), np.empty((0, k), dtype=np.int64)

        if faiss is None or self._index is None:
            xb = getattr(self, "_xb", None)
            if xb is None or xb.shape[0] == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._as_f32(xb)
            xq2 = (xq * xq).sum(axis=1, keepdims=True)
            xb2 = (xb * xb).sum(axis=1, keepdims=True).T
            dists = xq2 + xb2 - 2.0 * (xq @ xb.T)
            idx = np.argpartition(dists, kth=min(k - 1, dists.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dd = dists[row, idx]
            order = np.argsort(dd, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dd[row, order].astype(np.float32, copy=False)
            return D, I

        faiss.omp_set_num_threads(self.n_threads)
        if self.nprobe is not None:
            try:
                self._index.nprobe = int(self.nprobe)
            except Exception:
                pass
        D, I = self._index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I