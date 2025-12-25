import os
import time
from typing import Tuple, Optional, List

import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.num_threads = int(kwargs.get("num_threads", min(8, os.cpu_count() or 1)))
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 512))

        self.auto_tune = bool(kwargs.get("auto_tune", True))
        self.auto_tune_target_ms = float(kwargs.get("auto_tune_target_ms", 6.9))
        self.auto_tune_min_ntotal = int(kwargs.get("auto_tune_min_ntotal", 200_000))
        self.auto_tune_nq = int(kwargs.get("auto_tune_nq", 1000))
        self.auto_tune_efs: List[int] = list(kwargs.get("auto_tune_efs", [256, 384, 512, 768, 1024, 1536]))

        self._ntotal = 0
        self._tuned = False

        if faiss is None:
            self.index = None
            self._xb = None
            return

        faiss.omp_set_num_threads(self.num_threads)

        metric = kwargs.get("metric", "l2")
        if isinstance(metric, str):
            metric = metric.lower()
        if metric in ("l2", "euclidean", "ip2l2"):
            faiss_metric = faiss.METRIC_L2
        elif metric in ("ip", "inner_product"):
            faiss_metric = faiss.METRIC_INNER_PRODUCT
        else:
            faiss_metric = faiss.METRIC_L2

        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss_metric)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        self.index.verbose = bool(kwargs.get("verbose", False))

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")
        xb = np.ascontiguousarray(xb)

        if faiss is None:
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack((self._xb, xb))
            self._ntotal = int(self._xb.shape[0])
            return

        self.index.add(xb)
        self._ntotal = int(self.index.ntotal)

        if self.auto_tune and (not self._tuned) and self._ntotal >= self.auto_tune_min_ntotal:
            self._auto_tune_ef_search(xb)

    def _auto_tune_ef_search(self, xb_last: np.ndarray) -> None:
        if faiss is None or self.index is None:
            self._tuned = True
            return

        nq = min(self.auto_tune_nq, int(xb_last.shape[0]))
        if nq <= 0:
            self._tuned = True
            return

        if xb_last.shape[0] == nq:
            q = xb_last
        else:
            step = max(1, xb_last.shape[0] // nq)
            q = xb_last[::step][:nq]
            if q.shape[0] < nq:
                q = xb_last[:nq]
        q = np.ascontiguousarray(q, dtype=np.float32)

        # Warm-up
        old_ef = int(self.index.hnsw.efSearch)
        try:
            self.index.hnsw.efSearch = max(64, min(old_ef, 256))
            _ = self.index.search(q[: min(64, q.shape[0])], 1)
        except Exception:
            pass

        best_ef = max(64, old_ef)
        for ef in self.auto_tune_efs:
            ef = int(ef)
            if ef <= 0:
                continue
            try:
                self.index.hnsw.efSearch = ef
                t0 = time.perf_counter()
                _ = self.index.search(q, 1)
                t1 = time.perf_counter()
                ms_per_q = (t1 - t0) * 1000.0 / max(1, q.shape[0])
                if ms_per_q <= self.auto_tune_target_ms:
                    best_ef = ef
                else:
                    break
            except Exception:
                break

        self.ef_search = int(best_ef)
        self.index.hnsw.efSearch = int(best_ef)
        self._tuned = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")
        xq = np.ascontiguousarray(xq)

        if faiss is None or self.index is None:
            xb = self._xb
            if xb is None or xb.shape[0] == 0:
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)
            xb = np.ascontiguousarray(xb, dtype=np.float32)
            xq2 = np.sum(xq * xq, axis=1, keepdims=True)
            xb2 = np.sum(xb * xb, axis=1, keepdims=True).T
            dists = xq2 + xb2 - 2.0 * (xq @ xb.T)
            idx = np.argpartition(dists, k - 1, axis=1)[:, :k]
            row = np.arange(xq.shape[0])[:, None]
            dd = dists[row, idx]
            ord2 = np.argsort(dd, axis=1)
            idx = idx[row, ord2].astype(np.int64, copy=False)
            dd = dd[row, ord2].astype(np.float32, copy=False)
            return dd, idx

        self.index.hnsw.efSearch = int(self.ef_search)
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I