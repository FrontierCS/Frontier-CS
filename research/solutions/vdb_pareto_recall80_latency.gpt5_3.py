import numpy as np
import os
from typing import Tuple

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 8))
        self.M = int(kwargs.get("M", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.refine_k = int(kwargs.get("refine_k", 32))
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.train_size = int(kwargs.get("train_size", 200000))
        self.seed = int(kwargs.get("seed", 123))
        self.threads = int(kwargs.get("threads", 0))
        self.rng = np.random.RandomState(self.seed)

        self.faiss_index = None
        self.ntotal = 0

        if faiss is None:
            self.xb = None
        else:
            self._build_faiss_index()

    def _build_faiss_index(self):
        # Set FAISS thread count
        try:
            threads = self.threads if self.threads > 0 else (os.cpu_count() or 1)
            faiss.omp_set_num_threads(int(threads))
        except Exception:
            pass

        quantizer = faiss.IndexFlatL2(self.dim)
        ivfpq = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.M, self.nbits)
        ivfpq.by_residual = True
        try:
            ivfpq.use_precomputed_table = 1
        except Exception:
            pass

        index = ivfpq
        if self.use_opq:
            opq = faiss.OPQMatrix(self.dim, self.M)
            index = faiss.IndexPreTransform(opq, index)

        if self.refine_k and self.refine_k > 1:
            refine = faiss.IndexRefineFlat(index)
            try:
                refine.k_factor = int(self.refine_k)
            except Exception:
                pass
            self.faiss_index = refine
        else:
            self.faiss_index = index

        ivf = self._get_ivf_index()
        if ivf is not None:
            ivf.nprobe = self.nprobe

    def _get_ivf_index(self):
        if faiss is None or self.faiss_index is None:
            return None
        idx = self.faiss_index
        try:
            if isinstance(idx, faiss.IndexRefineFlat):
                idx = idx.base_index
            if isinstance(idx, faiss.IndexPreTransform):
                idx = faiss.downcast_index(idx.index)
            if isinstance(idx, faiss.IndexIVF):
                return idx
        except Exception:
            pass
        return None

    def add(self, xb: np.ndarray) -> None:
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dim matching initialization")

        if faiss is None:
            if self.ntotal == 0:
                self.xb = xb.copy()
            else:
                self.xb = np.vstack([self.xb, xb])
            self.ntotal = self.xb.shape[0]
            return

        if not self.faiss_index.is_trained:
            n_train = min(self.train_size, xb.shape[0])
            train_idx = self.rng.randint(0, xb.shape[0], size=n_train)
            xtrain = xb[train_idx].copy()
            self.faiss_index.train(xtrain)

        self.faiss_index.add(xb)
        self.ntotal = int(self.faiss_index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dim matching initialization")

        if k <= 0:
            raise ValueError("k must be >= 1")

        if faiss is None:
            if self.ntotal == 0:
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), -np.ones((nq, k), dtype=np.int64)
            # Naive exact search (fallback)
            xb = self.xb
            # Compute squared L2 distances using efficient batch computation
            q_norms = (xq ** 2).sum(axis=1, keepdims=True)
            b_norms = (xb ** 2).sum(axis=1, keepdims=True).T
            distances = q_norms + b_norms - 2.0 * np.dot(xq, xb.T)
            distances = np.maximum(distances, 0.0).astype(np.float32)
            idx_part = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
            part_vals = distances[np.arange(distances.shape[0])[:, None], idx_part]
            order = np.argsort(part_vals, axis=1)
            final_idx = idx_part[np.arange(idx_part.shape[0])[:, None], order]
            final_dist = distances[np.arange(distances.shape[0])[:, None], final_idx]
            return final_dist.astype(np.float32), final_idx.astype(np.int64)

        ivf = self._get_ivf_index()
        if ivf is not None:
            ivf.nprobe = self.nprobe

        D, I = self.faiss_index.search(xq, k)
        if D is None or I is None:
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), -np.ones((nq, k), dtype=np.int64)
        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)