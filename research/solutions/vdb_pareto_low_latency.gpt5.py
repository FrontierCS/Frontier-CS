import numpy as np
import faiss
import os
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim

        # Core IVF-PQ params
        self.nlist = int(kwargs.get('nlist', 16384))
        self.m = int(kwargs.get('m', 16))  # number of PQ subvectors
        self.nbits = int(kwargs.get('nbits', 8))  # bits per PQ subvector
        self.nprobe = int(kwargs.get('nprobe', 5))

        # HNSW coarse quantizer params
        self.hnsw_m = int(kwargs.get('hnsw_m', 32))
        self.hnsw_ef_construction = int(kwargs.get('hnsw_ef_construction', 40))
        self.hnsw_ef_search = int(kwargs.get('hnsw_ef_search', max(32, 2 * self.nprobe)))

        # Training subset size
        self.train_size = int(kwargs.get('train_size', 200000))

        # Threading
        self.faiss_threads = int(kwargs.get('faiss_threads', min(8, os.cpu_count() or 1)))
        faiss.omp_set_num_threads(self.faiss_threads)

        # Precompute tables for faster scans
        self.use_precomputed_tables = bool(kwargs.get('use_precomputed_tables', True))
        # Threshold for using precomputed tables, 0 to always use them
        self.scan_table_threshold = int(kwargs.get('scan_table_threshold', 0))

        self.metric = faiss.METRIC_L2

        self.quantizer = None
        self.index = None

    def _create_index(self):
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
        quantizer.hnsw.efConstruction = self.hnsw_ef_construction
        quantizer.hnsw.efSearch = self.hnsw_ef_search

        index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits, self.metric)
        index.nprobe = self.nprobe

        # Enable precomputed tables for faster ADC if available
        try:
            index.use_precomputed_table = 1 if self.use_precomputed_tables else 0
        except Exception:
            pass
        try:
            index.scan_table_threshold = self.scan_table_threshold
        except Exception:
            pass

        self.quantizer = quantizer
        self.index = index

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)

        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dtype float32")

        if self.index is None:
            self._create_index()

        if not self.index.is_trained:
            N = xb.shape[0]
            train_size = min(self.train_size, N)
            # Ensure at least nlist samples for training
            if train_size < self.nlist:
                train_size = min(N, self.nlist)

            if N > train_size:
                rng = np.random.default_rng(123)
                idx = rng.choice(N, size=train_size, replace=False)
                xt = np.ascontiguousarray(xb[idx])
            else:
                xt = xb

            self.index.train(xt)

            # Ensure efSearch is set post training (quantizer gets populated with centroids)
            try:
                self.quantizer.hnsw.efSearch = self.hnsw_ef_search
            except Exception:
                pass

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)

        if self.index is None or self.index.ntotal == 0:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = -np.ones((nq, k), dtype=np.int64)
            return D, I

        # Set search params
        self.index.nprobe = self.nprobe
        try:
            self.quantizer.hnsw.efSearch = self.hnsw_ef_search
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
