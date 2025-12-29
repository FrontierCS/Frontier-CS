import numpy as np
from typing import Tuple
import faiss
import multiprocessing


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters with defaults tuned for low-latency, reasonable recall
        self.nlist = int(kwargs.get("nlist", 8192))
        self.M = int(kwargs.get("M", 16))  # PQ subquantizers
        self.nbits = int(kwargs.get("nbits", 8))  # bits per subquantizer
        self.nprobe = int(kwargs.get("nprobe", 8))
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.train_size = int(kwargs.get("train_size", 120000))
        self.seed = int(kwargs.get("seed", 123))
        self.threads = int(kwargs.get("threads", 0))  # 0 -> use all

        self.index = None
        self.trained = False
        self.ntotal = 0

        # Set FAISS threading
        try:
            if self.threads > 0:
                faiss.omp_set_num_threads(self.threads)
            else:
                faiss.omp_set_num_threads(max(1, multiprocessing.cpu_count() or 1))
        except Exception:
            pass

    def _build_index(self):
        if self.use_opq:
            # OPQ improves recall with minimal overhead; good for strict latency
            desc = f"OPQ{self.M}_64,IVF{self.nlist},PQ{self.M}"
            self.index = faiss.index_factory(self.dim, desc, faiss.METRIC_L2)
        else:
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.M, self.nbits)
            self.index.metric_type = faiss.METRIC_L2
        self._set_nprobe()

    def _set_nprobe(self):
        if self.index is None:
            return
        try:
            ps = faiss.ParameterSpace()
            ps.set_index_parameter(self.index, "nprobe", self.nprobe)
        except Exception:
            try:
                ivf = faiss.extract_index_ivf(self.index)
                ivf.nprobe = self.nprobe
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        if self.index is None:
            self._build_index()

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        n_add = xb.shape[0]
        if n_add == 0:
            return

        if not self.trained:
            n_train = min(self.train_size, n_add)
            if n_train > 0:
                rs = np.random.RandomState(self.seed)
                if n_train < n_add:
                    idx = rs.choice(n_add, n_train, replace=False)
                    train_x = xb[idx]
                else:
                    train_x = xb
                self.index.train(train_x)
                self.trained = True
                self._set_nprobe()

        self.index.add(xb)
        try:
            self.ntotal = int(self.index.ntotal)
        except Exception:
            # For IndexPreTransform, ntotal is forwarded; still safe.
            self.ntotal += n_add

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        nq = xq.shape[0]
        k = int(k)

        if self.index is None or self.ntotal == 0 or k <= 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        self._set_nprobe()
        k_eff = min(k, self.ntotal)
        D, I = self.index.search(xq, k_eff)

        if k_eff < k:
            Dpad = np.full((nq, k), np.inf, dtype=np.float32)
            Ipad = np.full((nq, k), -1, dtype=np.int64)
            Dpad[:, :k_eff] = D
            Ipad[:, :k_eff] = I
            return Dpad, Ipad

        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)