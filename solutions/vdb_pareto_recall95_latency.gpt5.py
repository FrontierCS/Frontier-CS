import numpy as np
import faiss
import os
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.index_type = kwargs.get('index_type', 'hnsw')  # 'hnsw' or 'ivf_flat'
        self.metric = faiss.METRIC_L2

        # HNSW parameters
        self.M = int(kwargs.get('M', 32))
        self.ef_construction = int(kwargs.get('ef_construction', 200))
        self.ef_search = int(kwargs.get('ef_search', 350))

        # IVF parameters
        self.nlist = int(kwargs.get('nlist', 8192))
        self.nprobe = int(kwargs.get('nprobe', 128))
        self.train_size = int(kwargs.get('train_size', 50000))
        self.kmeans_niter = int(kwargs.get('kmeans_niter', 10))
        self.random_state = int(kwargs.get('random_state', 12345))

        # Threads
        nthreads = int(kwargs.get('num_threads', 0))
        if nthreads <= 0:
            nthreads = os.cpu_count() or 8
        try:
            faiss.omp_set_num_threads(nthreads)
        except Exception:
            pass

        self.index = None
        self.ntotal = 0

    def _build_hnsw(self):
        index = faiss.IndexHNSWFlat(self.dim, self.M)
        index.hnsw.efConstruction = self.ef_construction
        index.hnsw.efSearch = self.ef_search
        return index

    def _train_ivf_flat(self, xb: np.ndarray):
        # Ensure nlist is valid
        nlist_eff = min(self.nlist, max(1, xb.shape[0]))
        quantizer = faiss.IndexFlatL2(self.dim)
        index = faiss.IndexIVFFlat(quantizer, self.dim, nlist_eff, self.metric)

        # Select training set
        N = xb.shape[0]
        tsz = min(self.train_size, N)
        rng = np.random.default_rng(self.random_state)
        train_idx = rng.choice(N, size=tsz, replace=False)
        xtrain = xb[train_idx]

        # Train with faiss.Kmeans to control iterations (faster than default clustering settings)
        kmeans = faiss.Kmeans(self.dim, nlist_eff, niter=self.kmeans_niter, verbose=False, seed=self.random_state, spherical=False, nredo=1, max_points_per_centroid=1<<30)
        kmeans.train(xtrain)
        # Set centroids to quantizer
        quantizer.reset()
        quantizer.add(kmeans.centroids)

        # Mark trained
        index.nprobe = self.nprobe
        index.is_trained = True
        return index

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        if self.index is None:
            if self.index_type == 'hnsw':
                self.index = self._build_hnsw()
            else:
                self.index = self._train_ivf_flat(xb)

        # Adjust params if needed
        if isinstance(self.index, faiss.IndexIVF):
            self.index.nprobe = self.nprobe
        elif isinstance(self.index, faiss.IndexHNSW):
            self.index.hnsw.efSearch = self.ef_search

        self.index.add(xb)
        self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        if isinstance(self.index, faiss.IndexIVF):
            self.index.nprobe = self.nprobe
        elif isinstance(self.index, faiss.IndexHNSW):
            self.index.hnsw.efSearch = self.ef_search

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
