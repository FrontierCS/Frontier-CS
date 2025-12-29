import os
import numpy as np

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.index = None
        self.index_type = kwargs.get("index_type", "hnsw").lower()
        self._xb_count = 0

        # Threading setup
        num_threads = kwargs.get("num_threads", None)
        if faiss is not None:
            try:
                if num_threads is None:
                    num_threads = min(8, os.cpu_count() or 1)
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass

        if faiss is None:
            self._fallback_store = []

        if self.index_type == "hnsw":
            self.M = int(kwargs.get("M", 64))
            self.ef_construction = int(kwargs.get("ef_construction", 200))
            self.ef_search = int(kwargs.get("ef_search", 256))

            if faiss is not None:
                self.index = faiss.IndexHNSWFlat(self.dim, self.M)
                self.index.hnsw.efConstruction = self.ef_construction
                self.index.hnsw.efSearch = self.ef_search

        elif self.index_type == "ivf_flat":
            # IVF-Flat configuration
            self.nlist = int(kwargs.get("nlist", 32768))
            self.nprobe = int(kwargs.get("nprobe", 64))
            if faiss is not None:
                quantizer = faiss.IndexFlatL2(self.dim)
                self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
                # Training is deferred until add() is called with data
                self.index.nprobe = self.nprobe
        else:
            # Default to HNSW if unsupported type provided
            self.index_type = "hnsw"
            self.M = int(kwargs.get("M", 64))
            self.ef_construction = int(kwargs.get("ef_construction", 200))
            self.ef_search = int(kwargs.get("ef_search", 256))
            if faiss is not None:
                self.index = faiss.IndexHNSWFlat(self.dim, self.M)
                self.index.hnsw.efConstruction = self.ef_construction
                self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if faiss is None:
            self._fallback_store.append(xb.copy())
            self._xb_count += xb.shape[0]
            return

        if self.index_type == "ivf_flat":
            if not self.index.is_trained:
                # Train on a random subset to speed up training
                n_train = min(xb.shape[0], max(200000, self.nlist * 10))
                if n_train < xb.shape[0]:
                    rs = np.random.RandomState(1234)
                    idx = rs.choice(xb.shape[0], n_train, replace=False)
                    train_data = xb[idx]
                else:
                    train_data = xb
                self.index.train(train_data)
            self.index.add(xb)
        else:
            # HNSW and others
            self.index.add(xb)
        self._xb_count += xb.shape[0]

    def search(self, xq: np.ndarray, k: int):
        k = int(k)
        if k <= 0:
            return np.empty((xq.shape[0], 0), dtype=np.float32), np.empty((xq.shape[0], 0), dtype=np.int64)

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        if faiss is None:
            # Extremely slow fallback (not expected to be used in evaluation)
            xb = np.concatenate(self._fallback_store, axis=0) if self._fallback_store else np.empty((0, self.dim), dtype=np.float32)
            if xb.shape[0] == 0:
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), -np.ones((nq, k), dtype=np.int64)
            # Compute squared L2 distances
            xq_norms = (xq * xq).sum(axis=1, keepdims=True)
            xb_norms = (xb * xb).sum(axis=1, keepdims=True).T
            distances = xq_norms + xb_norms - 2.0 * xq @ xb.T
            distances = distances.astype(np.float32, copy=False)
            if k >= distances.shape[1]:
                idx = np.argsort(distances, axis=1)
                I = idx[:, :k]
                D = np.take_along_axis(distances, I, axis=1)
                return D.astype(np.float32), I.astype(np.int64)
            part = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
            row_idx = np.arange(distances.shape[0])[:, None]
            part_vals = distances[row_idx, part]
            order = np.argsort(part_vals, axis=1)
            I = part[row_idx, order]
            D = distances[row_idx, I]
            return D.astype(np.float32), I.astype(np.int64)

        if self.index_type == "hnsw":
            # Ensure efSearch is set appropriately
            try:
                if getattr(self.index.hnsw, "efSearch", None) is not None:
                    self.index.hnsw.efSearch = max(self.index.hnsw.efSearch, k)
            except Exception:
                pass

        elif self.index_type == "ivf_flat":
            try:
                self.index.nprobe = max(self.index.nprobe, 1)
            except Exception:
                pass

        D, I = self.index.search(xq, k)
        if D is None or I is None:
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), -np.ones((nq, k), dtype=np.int64)
        if D.dtype != np.float32:
            D = D.astype(np.float32)
        if I.dtype != np.int64:
            I = I.astype(np.int64)
        return D, I