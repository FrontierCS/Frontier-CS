import os
import numpy as np

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.xb_total = 0

        # Core parameters with sensible defaults for low latency
        self.nlist = int(kwargs.get("nlist", 8192))
        self.pq_m = int(kwargs.get("pq_m", kwargs.get("M_pq", 16)))
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.opq_m = int(kwargs.get("opq_m", self.pq_m))
        self.hnsw_m = int(kwargs.get("hnsw_m", kwargs.get("M", 32)))
        self.nprobe = int(kwargs.get("nprobe", 8))

        # HNSW quantizer parameters
        self.quantizer_efSearch = int(kwargs.get("quantizer_efSearch", 64))
        self.quantizer_efConstruction = int(kwargs.get("quantizer_efConstruction", 200))

        # Training parameters
        self.train_per_centroid = int(kwargs.get("train_per_centroid", 32))
        self.max_train_points = int(kwargs.get("max_train_points", 300000))
        self.kmeans_niter = int(kwargs.get("kmeans_niter", 20))
        self.opq_niter = int(kwargs.get("opq_niter", 20))

        # Threads
        self.num_threads = int(kwargs.get("num_threads", max(1, min(os.cpu_count() or 1, 8))))
        self.random_seed = int(kwargs.get("random_seed", 123))

        # Build once
        self._built = False
        self.index = None
        self.index_ivf = None
        self.pre = None

        # Fallback if faiss is not available
        self._fallback_xb = None

    def _set_threads(self):
        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.num_threads)
            except Exception:
                pass

    def _build_index(self):
        if faiss is None:
            # Fallback: brute-force (will be too slow; intended only for environments without faiss)
            self._fallback_xb = []
            self._built = True
            return

        rng = np.random.RandomState(self.random_seed)

        # Coarse quantizer: HNSW flat for low-latency coarse search
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m, faiss.METRIC_L2)
        quantizer.hnsw.efConstruction = self.quantizer_efConstruction
        quantizer.hnsw.efSearch = self.quantizer_efSearch

        # IVF-PQ index
        index_ivf = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.pq_m, 8, faiss.METRIC_L2)
        index_ivf.cp = faiss.ClusteringParameters()
        index_ivf.cp.niter = self.kmeans_niter
        index_ivf.cp.max_points_per_centroid = max(16, self.train_per_centroid)
        index_ivf.cp.min_points_per_centroid = 8

        # Prefer residual coding and precomputed tables for speed
        index_ivf.by_residual = True
        try:
            index_ivf.use_precomputed_table = 1
        except Exception:
            pass

        # Optional OPQ rotation
        if self.use_opq:
            pre = faiss.OPQMatrix(self.dim, self.opq_m)
            pre.niter = self.opq_niter
            pre.verbose = False
            index = faiss.IndexPreTransform(pre, index_ivf)
            self.pre = pre
        else:
            index = index_ivf
            self.pre = None

        self.index_ivf = index_ivf
        self.index = index
        self._built = True

        # Set search-time params
        self.index_ivf.nprobe = self.nprobe
        try:
            # ensure coarse quantizer efSearch is set
            if isinstance(self.index_ivf.quantizer, faiss.IndexHNSW):
                self.index_ivf.quantizer.hnsw.efSearch = self.quantizer_efSearch
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        n, d = xb.shape
        if d != self.dim:
            raise ValueError("Dimension mismatch in add: expected %d, got %d" % (self.dim, d))

        if not self._built:
            self._build_index()

        if faiss is None:
            # Fallback BF storage
            if self._fallback_xb is None:
                self._fallback_xb = []
            self._fallback_xb.append(xb.copy())
            self.xb_total += n
            return

        self._set_threads()

        # Train index if needed
        if not self.index.is_trained:
            # Subsample for training
            train_target = min(self.max_train_points, xb.shape[0], max(self.nlist * self.train_per_centroid, 10000))
            if train_target < xb.shape[0]:
                rng = np.random.RandomState(self.random_seed)
                idx = rng.choice(xb.shape[0], train_target, replace=False)
                xt = xb[idx]
            else:
                xt = xb

            self.index.train(xt)

            # After training, ensure quantizer params are set (HNSW graph built during centroid add)
            try:
                if isinstance(self.index_ivf.quantizer, faiss.IndexHNSW):
                    self.index_ivf.quantizer.hnsw.efSearch = self.quantizer_efSearch
            except Exception:
                pass

        # Add vectors
        self.index.add(xb)
        self.xb_total += n

        # Ensure search params remain set
        self.index_ivf.nprobe = self.nprobe
        try:
            if isinstance(self.index_ivf.quantizer, faiss.IndexHNSW):
                self.index_ivf.quantizer.hnsw.efSearch = self.quantizer_efSearch
        except Exception:
            pass

    def search(self, xq: np.ndarray, k: int):
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        nq, d = xq.shape
        if d != self.dim:
            raise ValueError("Dimension mismatch in search: expected %d, got %d" % (self.dim, d))

        if faiss is None or not self._built or self.index is None:
            # Fallback brute-force for environments without faiss
            if self._fallback_xb is None or len(self._fallback_xb) == 0:
                D = np.full((nq, k), np.inf, dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I
            xb = np.concatenate(self._fallback_xb, axis=0)
            # Compute L2 distances via efficient BLAS-like ops
            xq2 = np.sum(xq ** 2, axis=1, keepdims=True)
            xb2 = np.sum(xb ** 2, axis=1, keepdims=True).T
            distances = xq2 + xb2 - 2.0 * np.dot(xq, xb.T)
            idx = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dist_k = distances[row, idx]
            ord_k = np.argsort(dist_k, axis=1)
            I = idx[row, ord_k].astype(np.int64)
            D = dist_k[row, ord_k].astype(np.float32)
            return D, I

        self._set_threads()

        # Ensure parameters for search
        self.index_ivf.nprobe = self.nprobe
        try:
            if isinstance(self.index_ivf.quantizer, faiss.IndexHNSW):
                self.index_ivf.quantizer.hnsw.efSearch = self.quantizer_efSearch
        except Exception:
            pass

        D, I = self.index.search(xq, k)

        # Ensure correct dtypes and shapes
        D = np.ascontiguousarray(D, dtype=np.float32)
        I = np.ascontiguousarray(I, dtype=np.int64)
        return D, I