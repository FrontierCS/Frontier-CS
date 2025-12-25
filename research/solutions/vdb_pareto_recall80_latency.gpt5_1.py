import numpy as np
from typing import Tuple, Optional

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        nlist: int = 16384,
        nprobe: int = 3,
        pq_m: int = 16,
        pq_nbits: int = 8,
        use_opq: bool = True,
        train_size: int = 150000,
        hnsw_m: int = 32,
        hnsw_ef_search: int = 64,
        hnsw_ef_construction: int = 200,
        refine_factor: int = 8,
        num_threads: Optional[int] = None,
        seed: int = 12345,
        **kwargs,
    ):
        self.d = dim
        self.nlist = int(nlist)
        self.nprobe = int(nprobe)
        self.pq_m = int(pq_m)
        self.pq_nbits = int(pq_nbits)
        self.use_opq = bool(use_opq)
        self.train_size = int(train_size)
        self.hnsw_m = int(hnsw_m)
        self.hnsw_ef_search = int(hnsw_ef_search)
        self.hnsw_ef_construction = int(hnsw_ef_construction)
        self.refine_factor = int(refine_factor)
        self.seed = int(seed)

        self.num_threads = num_threads
        self._trained = False
        self._added = 0

        self.quantizer = None
        self.ivf = None
        self.base_index = None
        self.search_index = None

        # Thread setup for FAISS if available
        if faiss is not None:
            try:
                if self.num_threads is None:
                    self.num_threads = faiss.omp_get_max_threads()
                if self.num_threads is not None and self.num_threads > 0:
                    faiss.omp_set_num_threads(self.num_threads)
            except Exception:
                pass

        # Fallback flags if FAISS is missing
        self._fallback = faiss is None
        if self._fallback:
            # Fallback parameters for a very simple IVFFlat-like index
            self._centroids = None
            self._assign = None
            self._xb = None
            self._rng = np.random.RandomState(self.seed)

    def _build_faiss_index(self, xtrain: np.ndarray):
        d = self.d

        # Coarse quantizer: HNSW for fast nprobe selection
        self.quantizer = faiss.IndexHNSWFlat(d, self.hnsw_m)
        try:
            self.quantizer.hnsw.efSearch = self.hnsw_ef_search
            self.quantizer.hnsw.efConstruction = self.hnsw_ef_construction
        except Exception:
            pass

        # IVF+PQ
        self.ivf = faiss.IndexIVFPQ(self.quantizer, d, self.nlist, self.pq_m, self.pq_nbits)
        try:
            self.ivf.use_precomputed_table = 1
        except Exception:
            pass

        # Optional OPQ rotation
        if self.use_opq:
            opq = faiss.OPQMatrix(d, self.pq_m)
            self.base_index = faiss.IndexPreTransform(opq, self.ivf)
        else:
            self.base_index = self.ivf

        # Optional refine step for accuracy: re-rank a small factor of candidates using exact L2
        if self.refine_factor and self.refine_factor > 1:
            self.search_index = faiss.IndexRefineFlat(self.base_index)
            # Try to set k_factor on refine index
            set_ok = False
            try:
                self.search_index.k_factor = int(self.refine_factor)
                set_ok = True
            except Exception:
                pass
            if not set_ok:
                try:
                    ps = faiss.ParameterSpace()
                    ps.set_index_parameter(self.search_index, "k_factor", str(int(self.refine_factor)))
                except Exception:
                    pass
        else:
            self.search_index = self.base_index

        # Train
        self.base_index.train(xtrain)

        # IVF parameters
        try:
            self.ivf.nprobe = self.nprobe
        except Exception:
            pass

        # Precompute distance tables if supported
        try:
            if hasattr(self.ivf, "use_precomputed_table") and self.ivf.use_precomputed_table:
                try:
                    self.ivf.precompute_table()
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure HNSW quantizer parameters are up to date
        try:
            self.quantizer.hnsw.efSearch = self.hnsw_ef_search
        except Exception:
            pass

        self._trained = True

    def _train_if_needed_faiss(self, xb: np.ndarray):
        if self._trained:
            return
        n = xb.shape[0]
        train_n = min(self.train_size, n)
        rng = np.random.RandomState(self.seed)
        if n > train_n:
            idx = rng.choice(n, size=train_n, replace=False)
            xtrain = xb[idx].copy()
        else:
            xtrain = xb.copy()
        self._build_faiss_index(xtrain)

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb.astype(np.float32))
        if self._fallback:
            # Simple fallback: KMeans coarse clustering + list assignment (IVFFlat-like), exact within lists
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack((self._xb, xb))

            # Train centroids if not trained
            if self._centroids is None:
                n = self._xb.shape[0]
                train_n = min(self.train_size, n)
                # init centroids with random samples
                idx0 = self._rng.choice(n, size=min(self.nlist, train_n), replace=False)
                self._centroids = self._xb[idx0].copy()

                # A few kmeans iters to get coarse centroids
                iters = 8
                for _ in range(iters):
                    # Assign
                    dots = np.matmul(self._xb, self._centroids.T)
                    xb2 = (self._xb * self._xb).sum(axis=1, keepdims=True)
                    c2 = (self._centroids * self._centroids).sum(axis=1, keepdims=True).T
                    dists = xb2 + c2 - 2 * dots
                    assign = dists.argmin(axis=1)

                    # Update
                    for i in range(self._centroids.shape[0]):
                        mask = (assign == i)
                        if np.any(mask):
                            self._centroids[i] = self._xb[mask].mean(axis=0)
                self._assign = None  # will reassign on search
            self._added += xb.shape[0]
            return

        # FAISS path
        self._train_if_needed_faiss(xb)
        # Set parameters that may change
        try:
            self.ivf.nprobe = self.nprobe
        except Exception:
            pass
        try:
            self.quantizer.hnsw.efSearch = self.hnsw_ef_search
        except Exception:
            pass

        self.search_index.add(xb)
        self._added += xb.shape[0]

    def _fallback_assign(self):
        # Assign all database vectors to nearest centroid
        dots = np.matmul(self._xb, self._centroids.T)
        xb2 = (self._xb * self._xb).sum(axis=1, keepdims=True)
        c2 = (self._centroids * self._centroids).sum(axis=1, keepdims=True).T
        dists = xb2 + c2 - 2 * dots
        self._assign = dists.argmin(axis=1)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.ascontiguousarray(xq.astype(np.float32))

        if self._fallback:
            # Naive IVF-Flat fallback: nprobe nearest centroids, exact scan within lists
            if self._centroids is None:
                # No data added; return empty results
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)
            if self._assign is None:
                self._fallback_assign()

            # Centroid search
            dots = np.matmul(xq, self._centroids.T)
            xq2 = (xq * xq).sum(axis=1, keepdims=True)
            c2 = (self._centroids * self._centroids).sum(axis=1, keepdims=True).T
            cdists = xq2 + c2 - 2 * dots
            # pick nprobe
            nprobe = min(self.nprobe, self._centroids.shape[0])
            cand_lists = np.argpartition(cdists, nprobe - 1, axis=1)[:, :nprobe]

            # exact scan (L2) within candidate lists
            nq = xq.shape[0]
            D = np.full((nq, k), np.float32(np.inf), dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)

            # Build inverted lists
            lists = [[] for _ in range(self._centroids.shape[0])]
            for idx, cid in enumerate(self._assign):
                lists[cid].append(idx)
            lists = [np.array(l, dtype=np.int64) if len(l) > 0 else None for l in lists]

            for qi in range(nq):
                candidates = []
                for cid in cand_lists[qi]:
                    lid = int(cid)
                    if lists[lid is not None]:
                        pass
                for cid in cand_lists[qi]:
                    lid = int(cid)
                    if lists[lid] is None or lists[lid].size == 0:
                        continue
                    ids = lists[lid]
                    xb_sub = self._xb[ids]
                    # exact L2 distances
                    diff = xb_sub - xq[qi]
                    dist_sub = np.einsum('ij,ij->i', diff, diff)
                    candidates.append((dist_sub, ids))
                if not candidates:
                    continue
                dist_all = np.concatenate([c[0] for c in candidates], axis=0)
                ids_all = np.concatenate([c[1] for c in candidates], axis=0)
                if dist_all.shape[0] <= k:
                    order = np.argsort(dist_all, kind='mergesort')
                    D[qi, :dist_all.shape[0]] = dist_all[order]
                    I[qi, :dist_all.shape[0]] = ids_all[order]
                else:
                    idx_part = np.argpartition(dist_all, k - 1)[:k]
                    vals = dist_all[idx_part]
                    ids_sel = ids_all[idx_part]
                    order = np.argsort(vals, kind='mergesort')
                    D[qi] = vals[order]
                    I[qi] = ids_sel[order]
            return D, I

        # FAISS path
        if not self._trained:
            # No data; return empty results
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        # Ensure params set at query time
        try:
            self.ivf.nprobe = self.nprobe
        except Exception:
            pass
        try:
            if hasattr(self.quantizer, "hnsw"):
                self.quantizer.hnsw.efSearch = self.hnsw_ef_search
        except Exception:
            pass

        D, I = self.search_index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
