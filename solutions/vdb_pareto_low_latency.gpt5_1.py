import numpy as np
import os
import threading

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.index = None
        self.next_id = 0
        self.metric = kwargs.get("metric", "l2")
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 16))
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_search = int(kwargs.get("hnsw_ef_search", 64))
        self.hnsw_ef_construction = int(kwargs.get("hnsw_ef_construction", 40))
        self.train_samples = int(kwargs.get("train_samples", 50000))
        self.random_seed = int(kwargs.get("seed", 12345))
        self._lock = threading.Lock()

        if faiss is not None:
            try:
                nt = os.cpu_count() or 1
                faiss.omp_set_num_threads(nt)
            except Exception:
                pass

        # Fallback buffers if faiss is unavailable
        self._xb_fallback = None

    def _ensure_faiss_index(self, xb: np.ndarray):
        if self.index is not None or faiss is None:
            return

        d = self.dim
        rng = np.random.RandomState(self.random_seed)
        nb = xb.shape[0]
        nsamp = min(self.train_samples, nb)
        if nsamp < self.nlist:
            # ensure at least nlist samples for training
            nsamp = self.nlist

        if nsamp == nb:
            xtrain = xb.copy()
        else:
            idx = rng.choice(nb, size=nsamp, replace=False)
            xtrain = xb[idx].copy()

        quantizer = faiss.IndexHNSWFlat(d, self.hnsw_m)
        quantizer.hnsw.efConstruction = self.hnsw_ef_construction
        metric = faiss.METRIC_L2

        ivf = faiss.IndexIVFFlat(quantizer, d, self.nlist, metric)
        # Train
        ivf.train(xtrain)
        # tune coarse search
        quantizer.hnsw.efSearch = self.hnsw_ef_search
        ivf.nprobe = self.nprobe

        self.index = ivf

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32, copy=False)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            xb = xb.reshape(-1, self.dim).astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if faiss is None:
            # fallback: store for brute-force
            with self._lock:
                if self._xb_fallback is None:
                    self._xb_fallback = xb.copy()
                else:
                    self._xb_fallback = np.vstack([self._xb_fallback, xb])
                self.next_id += xb.shape[0]
            return

        with self._lock:
            if self.index is None:
                self._ensure_faiss_index(xb)

            nb = xb.shape[0]
            ids = np.arange(self.next_id, self.next_id + nb, dtype=np.int64)
            self.index.add_with_ids(xb, ids)
            self.next_id += nb

    def search(self, xq: np.ndarray, k: int):
        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32, copy=False)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            xq = xq.reshape(-1, self.dim).astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)
        nq = xq.shape[0]
        k = int(k)

        if faiss is None or self.index is None:
            # fallback brute-force
            if self._xb_fallback is None or self._xb_fallback.shape[0] == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = self._xb_fallback
            # compute distances
            # L2-squared distances: ||x||^2 + ||y||^2 - 2 x.y
            xq_norms = (xq ** 2).sum(axis=1, keepdims=True)
            xb_norms = (xb ** 2).sum(axis=1, keepdims=True).T
            distances = xq_norms + xb_norms - 2.0 * (xq @ xb.T)
            # select top-k smallest
            if k >= distances.shape[1]:
                idx = np.argsort(distances, axis=1)[:, :k]
            else:
                idx = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
                # sort within top-k
                row_idx = np.arange(nq)[:, None]
                topk_dist = distances[row_idx, idx]
                order = np.argsort(topk_dist, axis=1)
                idx = idx[row_idx, order]
            D = distances[np.arange(nq)[:, None], idx].astype(np.float32, copy=False)
            I = idx.astype(np.int64, copy=False)
            return D, I

        # Ensure parameters at search time
        self.index.nprobe = self.nprobe
        if isinstance(self.index.quantizer, faiss.IndexHNSWFlat):
            self.index.quantizer.hnsw.efSearch = self.hnsw_ef_search

        D, I = self.index.search(xq, k)
        if not isinstance(D, np.ndarray):
            D = np.array(D, dtype=np.float32, copy=False).reshape(nq, k)
        if not isinstance(I, np.ndarray):
            I = np.array(I, dtype=np.int64, copy=False).reshape(nq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
