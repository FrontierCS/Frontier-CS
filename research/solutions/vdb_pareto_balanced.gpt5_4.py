import os
import time
from typing import Tuple

import numpy as np

try:
    import faiss
    HAVE_FAISS = True
except Exception:
    HAVE_FAISS = False


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.ntotal = 0

        # Select algorithm: default to IVF-Flat for strong recall-speed balance
        self.algorithm = kwargs.get("algorithm", "ivf_flat")

        # Thread configuration
        self.num_threads = int(kwargs.get("num_threads", min(8, os.cpu_count() or 8)))
        if HAVE_FAISS:
            try:
                faiss.omp_set_num_threads(self.num_threads)
            except Exception:
                pass

        # Latency target (ms)
        self.latency_target_ms = float(kwargs.get("latency_target_ms", 5.775))

        # IVF parameters
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.train_samples = int(kwargs.get("train_samples", 100000))

        # HNSW parameters (if used)
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 128))
        self.auto_tune_ef = bool(kwargs.get("auto_tune_ef", True))
        self._ef_tuned = False

        # Optional: Fallback to HNSW if IVF is not requested
        if self.algorithm not in ("ivf_flat", "hnsw"):
            self.algorithm = "ivf_flat"

        self.index = None

        # Fallback brute force index if FAISS missing
        self._numpy_xb = None

    def _ensure_faiss_index(self):
        if not HAVE_FAISS:
            return

        if self.index is not None:
            return

        if self.algorithm == "ivf_flat":
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            try:
                self.index.nprobe = self.nprobe
            except Exception:
                pass
        elif self.algorithm == "hnsw":
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.asarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if HAVE_FAISS:
            self._ensure_faiss_index()

            if self.algorithm == "ivf_flat":
                if not self.index.is_trained:
                    ntrain = min(self.train_samples, xb.shape[0])
                    if ntrain < self.nlist:
                        ntrain = min(self.nlist, xb.shape[0])
                    if ntrain < 10000:
                        ntrain = min(10000, xb.shape[0])
                    if ntrain > 0 and ntrain < xb.shape[0]:
                        rng = np.random.default_rng(123)
                        idx = rng.choice(xb.shape[0], ntrain, replace=False)
                        xt = xb[idx]
                    else:
                        xt = xb
                    xt = np.ascontiguousarray(xt, dtype=np.float32)
                    self.index.train(xt)
                self.index.add(xb)
                try:
                    self.index.nprobe = self.nprobe
                except Exception:
                    pass
            elif self.algorithm == "hnsw":
                self.index.add(xb)
        else:
            # Fallback brute force storage
            if self._numpy_xb is None:
                self._numpy_xb = xb.copy()
            else:
                self._numpy_xb = np.vstack([self._numpy_xb, xb])

        self.ntotal += xb.shape[0]

    def _auto_tune_hnsw_ef(self, xq: np.ndarray, k: int) -> None:
        if not HAVE_FAISS or self.index is None or self._ef_tuned:
            return
        if not hasattr(self.index, "hnsw") or not self.auto_tune_ef:
            self._ef_tuned = True
            return

        # Quick check using a small subset to see if we exceed the target latency
        nq = xq.shape[0]
        if nq == 0:
            self._ef_tuned = True
            return
        sample_nq = min(48, nq)
        xq_sample = xq[:sample_nq]

        # Measure with current efSearch
        start = time.time()
        _ = self.index.search(xq_sample, max(1, int(k)))
        elapsed_ms = (time.time() - start) * 1000.0 / sample_nq

        if elapsed_ms > self.latency_target_ms:
            # Reduce efSearch proportionally to meet target
            current_ef = int(self.index.hnsw.efSearch)
            # Avoid division by zero
            if elapsed_ms > 0:
                ratio = self.latency_target_ms / elapsed_ms
            else:
                ratio = 0.5
            new_ef = max(16, int(max(10, current_ef * ratio * 0.98)))
            new_ef = min(new_ef, current_ef)
            if new_ef < current_ef:
                self.index.hnsw.efSearch = new_ef

        self._ef_tuned = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            xq = np.asarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        if HAVE_FAISS and self.index is not None:
            if self.algorithm == "ivf_flat":
                try:
                    self.index.nprobe = self.nprobe
                except Exception:
                    pass
                D, I = self.index.search(xq, int(k))
                return D, I
            elif self.algorithm == "hnsw":
                self._auto_tune_hnsw_ef(xq, int(k))
                D, I = self.index.search(xq, int(k))
                return D, I

        # Fallback brute force (slow; used only if Faiss is unavailable)
        xb = self._numpy_xb
        if xb is None or xb.shape[0] == 0:
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # Compute distances in blocks to limit memory
        nq, d = xq.shape
        N = xb.shape[0]
        k = int(k)
        topk_dist = np.empty((nq, k), dtype=np.float32)
        topk_idx = np.empty((nq, k), dtype=np.int64)

        batch = 65536 // max(d, 1)
        batch = max(1, min(2048, batch))

        for i0 in range(0, N, batch):
            i1 = min(N, i0 + batch)
            xbb = xb[i0:i1]
            # Compute squared L2: ||x||^2 + ||y||^2 - 2x.y
            xq_norms = np.sum(xq ** 2, axis=1, keepdims=True)
            xb_norms = np.sum(xbb ** 2, axis=1, keepdims=True).T
            dots = xq @ xbb.T
            dists = xq_norms + xb_norms - 2 * dots
            if i0 == 0:
                idx = np.argpartition(dists, kth=min(k - 1, dists.shape[1] - 1), axis=1)[:, :k]
                part = dists[np.arange(nq)[:, None], idx]
                order = np.argsort(part, axis=1)
                topk_idx = (idx[np.arange(nq)[:, None], order] + i0).astype(np.int64)
                topk_dist = np.take_along_axis(part, order, axis=1).astype(np.float32)
            else:
                # Merge with previous topk
                merged_idx = []
                merged_dist = []
                for qi in range(nq):
                    cand_dist = np.hstack([topk_dist[qi], dists[qi]])
                    cand_idx = np.hstack([topk_idx[qi], np.arange(i0, i1, dtype=np.int64)])
                    best_idx = np.argpartition(cand_dist, kth=k - 1)[:k]
                    best_sorted = best_idx[np.argsort(cand_dist[best_idx])]
                    merged_idx.append(cand_idx[best_sorted])
                    merged_dist.append(cand_dist[best_sorted])
                topk_idx = np.vstack(merged_idx).astype(np.int64)
                topk_dist = np.vstack(merged_dist).astype(np.float32)

        return topk_dist, topk_idx