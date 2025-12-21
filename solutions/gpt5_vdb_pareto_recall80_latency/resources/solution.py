import numpy as np
from typing import Tuple, Optional

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters with sensible defaults for Recall80 Latency tier
        self.nlist: int = int(kwargs.get("nlist", 4096))
        self.m_pq: int = int(kwargs.get("m", 16))  # number of PQ subvectors
        self.nbits: int = int(kwargs.get("nbits", 8))  # bits per PQ codebook
        self.nprobe: int = int(kwargs.get("nprobe", 16))
        self.use_opq: bool = bool(kwargs.get("use_opq", True))
        self.train_size: int = int(kwargs.get("train_size", 200000))
        self.refine_factor: int = int(kwargs.get("refine_factor", 8))  # refine k_factor
        self.random_seed: int = int(kwargs.get("seed", 123))
        self.num_threads: Optional[int] = kwargs.get("num_threads", None)

        self.index = None  # final index (possibly IndexRefineFlat)
        self._base_index = None  # inner base index (IVFPQ possibly inside PreTransform)
        self._is_trained = False
        self._ntotal = 0

        # Validate divisibility for PQ/OPQ
        if self.dim % self.m_pq != 0:
            # Adjust m_pq to a divisor of dim if necessary
            # Find largest divisor of dim <= requested m_pq
            div = None
            for m in range(self.m_pq, 0, -1):
                if self.dim % m == 0:
                    div = m
                    break
            if div is None:
                div = 1
            self.m_pq = div

        if faiss is not None:
            try:
                if self.num_threads is None:
                    th = faiss.omp_get_max_threads()
                else:
                    th = int(self.num_threads)
                if th > 0:
                    faiss.omp_set_num_threads(th)
            except Exception:
                pass

    def _build_index(self, train_x: np.ndarray):
        if faiss is None:
            raise RuntimeError("FAISS library is required for this index.")

        d = self.dim
        # Coarse quantizer
        quantizer = faiss.IndexFlatL2(d)

        # Base IVF-PQ index
        ivfpq = faiss.IndexIVFPQ(quantizer, d, self.nlist, self.m_pq, self.nbits, faiss.METRIC_L2)
        ivfpq.by_residual = True

        base_index = ivfpq
        # Optional OPQ transform to improve recall for same code size
        if self.use_opq:
            opq = faiss.OPQMatrix(d, self.m_pq)
            base_index = faiss.IndexPreTransform(opq, ivfpq)

        # Training
        # Ensure contiguous float32
        train_x = np.ascontiguousarray(train_x, dtype=np.float32)
        base_index.train(train_x)

        # Use refine flat to re-rank a small candidate set for better recall
        refine = faiss.IndexRefineFlat(base_index)
        refine.k_factor = max(1, int(self.refine_factor))

        # Set nprobe on the inner IVF
        try:
            ivf = faiss.extract_index_ivf(refine)
            if ivf is not None:
                ivf.nprobe = int(self.nprobe)
        except Exception:
            pass

        # Try to enable precomputed tables on IVFPQ for speed
        try:
            inner_ivf = faiss.extract_index_ivf(refine)
            pq = faiss.downcast_index(inner_ivf)
            if hasattr(pq, "use_precomputed_table"):
                pq.use_precomputed_table = 1
        except Exception:
            pass

        self.index = refine
        self._base_index = base_index
        self._is_trained = True

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must have shape (N, dim) with dim matching initialization")

        if self.index is None:
            # Train on a random subset of the first add batch
            N = xb.shape[0]
            rs = np.random.RandomState(self.random_seed)
            if N > self.train_size:
                idx = rs.choice(N, self.train_size, replace=False)
                train_x = xb[idx]
            else:
                train_x = xb
            self._build_index(train_x)

        # Ensure FAISS uses desired threads
        if faiss is not None:
            try:
                if self.num_threads is None:
                    th = faiss.omp_get_max_threads()
                else:
                    th = int(self.num_threads)
                if th > 0:
                    faiss.omp_set_num_threads(th)
            except Exception:
                pass

        # Add vectors
        self.index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or not self._is_trained:
            raise RuntimeError("Index not built/trained. Call add() before search().")
        if k <= 0:
            raise ValueError("k must be positive")

        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must have shape (nq, dim) with dim matching initialization")

        # Ensure FAISS uses desired threads
        if faiss is not None:
            try:
                if self.num_threads is None:
                    th = faiss.omp_get_max_threads()
                else:
                    th = int(self.num_threads)
                if th > 0:
                    faiss.omp_set_num_threads(th)
            except Exception:
                pass

        # Set nprobe on each search call (in case user changed it)
        try:
            ivf = faiss.extract_index_ivf(self.index)
            if ivf is not None:
                ivf.nprobe = int(self.nprobe)
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes and shapes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
