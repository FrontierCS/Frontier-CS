import os
import numpy as np
from typing import Tuple, Optional

try:
    import faiss  # type: ignore
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 640))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))

        self.k_factor = int(kwargs.get("k_factor", 128))

        self.train_size = int(kwargs.get("train_size", 200_000))
        self.min_train_size = int(kwargs.get("min_train_size", 50_000))

        self.niter = int(kwargs.get("niter", 12))
        self.opq_niter = int(kwargs.get("opq_niter", 16))
        self.use_opq = bool(kwargs.get("use_opq", True))

        self.n_threads = int(kwargs.get("n_threads", max(1, min(8, (os.cpu_count() or 8)))))

        self._rng = np.random.default_rng(int(kwargs.get("seed", 12345)))

        self._index = None
        self._buffer = []
        self._buffer_rows = 0

        self._xb_fallback = None
        self._xb_norms_fallback = None

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

            self._index = self._build_faiss_index()

    def _build_faiss_index(self):
        quantizer = faiss.IndexFlatL2(self.dim)
        ivfpq = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, faiss.METRIC_L2)
        try:
            ivfpq.cp.niter = self.niter
            ivfpq.cp.seed = 12345
            ivfpq.cp.min_points_per_centroid = 5
        except Exception:
            pass
        ivfpq.nprobe = self.nprobe

        base = ivfpq
        if self.use_opq:
            opq = faiss.OPQMatrix(self.dim, self.m)
            try:
                opq.niter = self.opq_niter
                opq.verbose = False
            except Exception:
                pass
            base = faiss.IndexPreTransform(opq, ivfpq)

        refine = faiss.IndexRefineFlat(base)
        try:
            refine.k_factor = self.k_factor
        except Exception:
            pass
        return refine

    def _is_trained(self) -> bool:
        if faiss is None or self._index is None:
            return self._xb_fallback is not None
        try:
            return bool(self._index.is_trained)
        except Exception:
            return False

    def _maybe_train_and_flush(self, xb_new: np.ndarray) -> None:
        if faiss is None or self._index is None:
            return

        if self._is_trained():
            return

        total_rows = self._buffer_rows + xb_new.shape[0]
        if total_rows < self.min_train_size:
            self._buffer.append(xb_new)
            self._buffer_rows = total_rows
            return

        if self._buffer:
            xb_all = np.vstack([*self._buffer, xb_new])
            self._buffer.clear()
            self._buffer_rows = 0
        else:
            xb_all = xb_new

        n = xb_all.shape[0]
        train_n = min(self.train_size, n)
        if train_n <= 0:
            return

        if train_n == n:
            train_x = xb_all
        else:
            sel = self._rng.choice(n, size=train_n, replace=False)
            train_x = xb_all[sel]

        train_x = np.ascontiguousarray(train_x, dtype=np.float32)
        self._index.train(train_x)
        self._index.add(np.ascontiguousarray(xb_all, dtype=np.float32))

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        if faiss is None or self._index is None:
            if self._xb_fallback is None:
                self._xb_fallback = xb.copy()
            else:
                self._xb_fallback = np.vstack([self._xb_fallback, xb])
            xb2 = self._xb_fallback
            self._xb_norms_fallback = (xb2 * xb2).sum(axis=1).astype(np.float32, copy=False)
            return

        if not self._is_trained():
            self._maybe_train_and_flush(xb)
            return

        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        nq = xq.shape[0]

        if faiss is None or self._index is None:
            xb = self._xb_fallback
            if xb is None or xb.shape[0] == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            xb_norms = self._xb_norms_fallback
            if xb_norms is None:
                xb_norms = (xb * xb).sum(axis=1).astype(np.float32, copy=False)
                self._xb_norms_fallback = xb_norms

            xq_norms = (xq * xq).sum(axis=1).astype(np.float32, copy=False)

            block = int(os.environ.get("BF_BLOCK", "50000"))
            best_D = np.full((nq, k), np.inf, dtype=np.float32)
            best_I = np.full((nq, k), -1, dtype=np.int64)

            for start in range(0, xb.shape[0], block):
                end = min(xb.shape[0], start + block)
                xb_block = xb[start:end]
                dots = xq @ xb_block.T
                dists = xq_norms[:, None] + xb_norms[start:end][None, :] - 2.0 * dots

                if k == 1:
                    idx = np.argmin(dists, axis=1)
                    dist = dists[np.arange(nq), idx]
                    better = dist < best_D[:, 0]
                    best_D[better, 0] = dist[better]
                    best_I[better, 0] = (start + idx[better]).astype(np.int64, copy=False)
                else:
                    idx = np.argpartition(dists, k - 1, axis=1)[:, :k]
                    dist = dists[np.arange(nq)[:, None], idx]
                    merged_D = np.concatenate([best_D, dist], axis=1)
                    merged_I = np.concatenate([best_I, (start + idx).astype(np.int64, copy=False)], axis=1)
                    sel = np.argpartition(merged_D, k - 1, axis=1)[:, :k]
                    best_D = merged_D[np.arange(nq)[:, None], sel]
                    best_I = merged_I[np.arange(nq)[:, None], sel]
                    order = np.argsort(best_D, axis=1)
                    best_D = best_D[np.arange(nq)[:, None], order]
                    best_I = best_I[np.arange(nq)[:, None], order]

            return best_D, best_I

        if not self._is_trained():
            raise RuntimeError("Index not trained. Call add() with enough data first.")

        try:
            base = self._index.base_index
            ivf = faiss.extract_index_ivf(base)
            if ivf is not None:
                ivf.nprobe = self.nprobe
        except Exception:
            pass

        D, I = self._index.search(xq, k)
        D = np.asarray(D, dtype=np.float32)
        I = np.asarray(I, dtype=np.int64)
        if D.shape != (nq, k) or I.shape != (nq, k):
            D = D.reshape(nq, k).astype(np.float32, copy=False)
            I = I.reshape(nq, k).astype(np.int64, copy=False)
        return D, I


__all__ = ["YourIndexClass"]