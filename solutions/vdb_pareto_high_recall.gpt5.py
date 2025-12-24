import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(
        self,
        dim: int,
        nlist: int = 32768,
        nprobe: int = 384,
        hnsw_m: int = 32,
        ef_search_coarse: int = 512,
        ef_construction: int = 200,
        training_samples: int = 200000,
        k_factor: int = 32,
        add_bs: int = 65536,
        seed: int = 123,
        num_threads: int = 0,
        **kwargs
    ):
        self.dim = dim
        self.nlist = int(kwargs.get("nlist", nlist))
        self.nprobe = int(kwargs.get("nprobe", nprobe))
        self.hnsw_m = int(kwargs.get("hnsw_m", hnsw_m))
        self.ef_search_coarse = int(kwargs.get("ef_search_coarse", ef_search_coarse))
        self.ef_construction = int(kwargs.get("ef_construction", ef_construction))
        self.training_samples = int(kwargs.get("training_samples", training_samples))
        self.k_factor = int(kwargs.get("k_factor", k_factor))
        self.add_bs = int(kwargs.get("add_bs", add_bs))
        self.seed = int(kwargs.get("seed", seed))
        self.num_threads = int(kwargs.get("num_threads", num_threads))
        self._rng = np.random.RandomState(self.seed)

        self.base_index = None
        self.index = None
        self._is_trained = False

        try:
            if self.num_threads and self.num_threads > 0:
                faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

    def _build_base_index(self):
        if self.base_index is not None:
            return
        quantizer = faiss.IndexHNSWFlat(self.dim, self.hnsw_m)
        try:
            quantizer.hnsw.efSearch = max(self.ef_search_coarse, self.nprobe)
            quantizer.hnsw.efConstruction = self.ef_construction
        except Exception:
            pass

        index_ivf = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        index_ivf.nprobe = self.nprobe
        self.base_index = index_ivf

        refine = faiss.IndexRefineFlat(self.base_index)
        refine.k_factor = max(1, self.k_factor)
        self.index = refine

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.shape[1] != self.dim:
            raise ValueError("Input dimension does not match index dimension.")
        self._build_base_index()

        if not self._is_trained:
            n_train = min(self.training_samples, xb.shape[0])
            idx = self._rng.choice(xb.shape[0], n_train, replace=False)
            xt = xb[idx]
            self.base_index.train(xt)
            try:
                # reset efSearch after training in case quantizer was re-initialized
                self.base_index.quantizer.hnsw.efSearch = max(self.ef_search_coarse, self.nprobe)
                self.base_index.quantizer.hnsw.efConstruction = self.ef_construction
            except Exception:
                pass
            self._is_trained = True

        bs = self.add_bs
        for i in range(0, xb.shape[0], bs):
            self.index.add(xb[i:i + bs])

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None or not self._is_trained:
            raise RuntimeError("Index not built or not trained. Call add() before search().")

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        try:
            ps = faiss.ParameterSpace()
            ps.set_index_parameter(self.index, "nprobe", self.nprobe)
        except Exception:
            if hasattr(self.base_index, "nprobe"):
                self.base_index.nprobe = self.nprobe

        try:
            self.base_index.quantizer.hnsw.efSearch = max(self.ef_search_coarse, self.nprobe)
        except Exception:
            pass

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
