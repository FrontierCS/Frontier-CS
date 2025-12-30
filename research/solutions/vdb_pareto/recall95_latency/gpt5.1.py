import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Optional kwargs:
            - index_type: 'ivf_flat' (default) or 'hnsw'
            - nlist: number of IVF lists (default: 4096)
            - nprobe: number of IVF probes at search (default: 128)
            - M: HNSW M parameter (default: 32)
            - ef_search: HNSW efSearch parameter (default: 128)
            - ef_construction: HNSW efConstruction parameter (default: 200)
            - num_threads: number of FAISS threads (default: min(cpu_count, faiss max))
        """
        self.dim = dim
        self.index = None

        # Configure threads for FAISS
        if "num_threads" in kwargs:
            threads = int(kwargs["num_threads"])
        else:
            try:
                import multiprocessing

                cpu_count = multiprocessing.cpu_count()
            except Exception:
                cpu_count = 1
            try:
                max_threads = faiss.omp_get_max_threads()
            except Exception:
                max_threads = cpu_count
            threads = max(1, min(cpu_count, max_threads))
        try:
            faiss.omp_set_num_threads(threads)
        except Exception:
            pass

        # Decide backend: IVF Flat (default) or HNSW
        requested_index_type = kwargs.get("index_type", None)
        if requested_index_type is not None:
            requested_index_type = str(requested_index_type).lower()

        # If HNSW-style parameters are passed, prefer HNSW backend
        if requested_index_type in {"hnsw", "hnswflat"} or "M" in kwargs or "ef_search" in kwargs:
            # HNSW backend
            self.index_type = "hnsw"
            self.M = int(kwargs.get("M", 32))
            self.ef_search = int(kwargs.get("ef_search", 128))
            self.ef_construction = int(kwargs.get("ef_construction", 200))

            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
            # Configure HNSW parameters
            self.index.hnsw.efSearch = self.ef_search
            self.index.hnsw.efConstruction = self.ef_construction
            self._ivf_trained = True  # for uniformity; HNSW doesn't require training
        else:
            # IVF Flat backend (high recall with generous latency budget)
            self.index_type = "ivf_flat"
            self.nlist = int(kwargs.get("nlist", 4096))
            # Higher nprobe for high recall; still fast under generous latency budget
            self.nprobe = int(kwargs.get("nprobe", 128))

            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            self.index.nprobe = self.nprobe
            self._ivf_trained = False

        # Training sample size for IVF
        self._max_train_points = int(kwargs.get("max_train_points", 256000))

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dim matching index.dimension")

        xb = np.ascontiguousarray(xb, dtype=np.float32)

        if self.index_type == "ivf_flat":
            # Train IVF quantizer on a subset if not already trained
            if not self.index.is_trained:
                n_train = min(self._max_train_points, xb.shape[0])
                if xb.shape[0] > n_train:
                    # Random subset for training
                    idx = np.random.choice(xb.shape[0], n_train, replace=False)
                    x_train = xb[idx]
                else:
                    x_train = xb
                x_train = np.ascontiguousarray(x_train, dtype=np.float32)
                self.index.train(x_train)

            self.index.add(xb)
        else:
            # HNSW: no separate training phase
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 (squared) distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        if xq is None:
            raise ValueError("xq must not be None")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dim matching index.dimension")

        if self.index.ntotal == 0:
            # No data: return empty results
            nq = xq.shape[0]
            return (
                np.full((nq, k), np.inf, dtype=np.float32),
                np.full((nq, k), -1, dtype=np.int64),
            )

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        if self.index_type == "ivf_flat":
            # Ensure nprobe is set (can be changed by user between calls)
            self.index.nprobe = self.nprobe
        else:
            # Ensure HNSW efSearch is set
            self.index.hnsw.efSearch = self.ef_search

        D, I = self.index.search(xq, k)
        return D, I