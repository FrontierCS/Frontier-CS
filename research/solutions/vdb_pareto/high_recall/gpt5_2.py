import os
import time
from typing import Tuple, Optional, List

import numpy as np

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        if faiss is None:
            raise RuntimeError("faiss is required for this solution")

        self.dim = int(dim)
        # Index type configuration
        self.index_type = str(kwargs.get("index_type", "hnsw")).lower()

        # HNSW parameters
        self.M = int(kwargs.get("M", 32))
        self.M = max(8, min(self.M, 64))
        self.ef_construction = int(kwargs.get("ef_construction", 300))
        self._ef_search_user = kwargs.get("ef_search", None)
        self.auto_tune = bool(kwargs.get("auto_tune", True if self._ef_search_user is None else False))

        # Latency target for auto-tuning (ms)
        self.latency_ms_target = float(kwargs.get("latency_ms_target", 7.7))
        # Slightly conservative target to account for variance
        self.latency_ms_target *= float(kwargs.get("latency_safety", 0.97))

        # Calibration settings
        self.calib_query_count = int(kwargs.get("calib_query_count", 128))
        self.calib_ef_candidates: Optional[List[int]] = kwargs.get("ef_candidates", None)

        # Threading
        self.num_threads = int(kwargs.get("num_threads", max(1, (os.cpu_count() or 8))))
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        # RNG seed
        self.seed = int(kwargs.get("seed", 12345))
        self.rng = np.random.RandomState(self.seed)

        # IVF params (not default; available if index_type is set accordingly)
        self.nlist = int(kwargs.get("nlist", 16384))
        self.nprobe = int(kwargs.get("nprobe", 128))
        self.use_ivf_hnsw_quantizer = bool(kwargs.get("ivf_use_hnsw_quantizer", False))
        self.quantizer_M = int(kwargs.get("quantizer_M", 32))

        # Internal FAISS index
        self.index = None
        self.trained = False

        # Create the index structure based on type
        self._create_index()

    def _create_index(self) -> None:
        if self.index_type == "hnsw":
            index = faiss.IndexHNSWFlat(self.dim, self.M)
            index.hnsw.efConstruction = self.ef_construction
            # defer setting efSearch until search/autotune
            self.index = index
            self.trained = True  # HNSWFlat does not need training
        elif self.index_type in ("ivf_flat", "ivf-hnsw", "ivf"):
            # Build an IVFFlat index, optionally with HNSW coarse quantizer
            if self.use_ivf_hnsw_quantizer or self.index_type == "ivf-hnsw":
                quantizer = faiss.IndexHNSWFlat(self.dim, self.quantizer_M)
                quantizer.hnsw.efConstruction = max(100, self.ef_construction // 2)
            else:
                quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
            index.nprobe = self.nprobe
            self.index = index
            self.trained = False
        else:
            # Fallback to HNSW if type unknown
            index = faiss.IndexHNSWFlat(self.dim, self.M)
            index.hnsw.efConstruction = self.ef_construction
            self.index = index
            self.trained = True

    def add(self, xb: np.ndarray) -> None:
        if self.index is None:
            self._create_index()

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}) and dtype float32")
        xb = np.ascontiguousarray(xb)

        # Train if necessary (IVF)
        if not self.trained and isinstance(self.index, faiss.IndexIVF):
            # Use a subset for training to reduce time if dataset is very large
            n_train = min(256 * self.nlist, xb.shape[0])
            if n_train < xb.shape[0]:
                train_idx = self.rng.choice(xb.shape[0], n_train, replace=False)
                train_x = xb[train_idx]
            else:
                train_x = xb

            self.index.train(train_x)
            self.trained = True

            # If quantizer is HNSW, set efSearch reasonably for coarse assignment
            if isinstance(self.index.quantizer, faiss.IndexHNSW):
                try:
                    self.index.quantizer.hnsw.efSearch = max(64, self.nprobe * 2)
                except Exception:
                    pass

        self.index.add(xb)

    def _autotune_hnsw_ef(self, xq: np.ndarray, k: int) -> int:
        # If user provided ef_search explicitly, respect it
        if self._ef_search_user is not None:
            ef = int(self._ef_search_user)
            try:
                self.index.hnsw.efSearch = ef
            except Exception:
                pass
            return ef

        # Candidate ef values
        if self.calib_ef_candidates is not None:
            candidates = sorted(int(v) for v in self.calib_ef_candidates if v and v > 0)
        else:
            # Reasonable sweep; start low and go up to aggressive
            # Adjust based on M to keep compute proportional
            base = [200, 280, 360, 440, 520, 600, 700, 800]
            if self.M >= 48:
                base = [240, 320, 400, 480, 560, 640, 740, 860]
            candidates = base

        # Sample a small subset of queries for calibration
        nq = xq.shape[0]
        calib_nq = min(max(64, self.calib_query_count), nq)
        # sample evenly across the batch to minimize cache effects
        if calib_nq < nq:
            step = max(1, nq // calib_nq)
            idx = np.arange(0, step * calib_nq, step, dtype=np.int64)
            xq_sample = xq[idx]
        else:
            xq_sample = xq

        # Guarantee contiguous memory and dtype
        xq_sample = np.ascontiguousarray(xq_sample.astype(np.float32, copy=False))

        # Try candidates and pick largest ef within target latency
        best_ef = candidates[0]
        for ef in candidates:
            try:
                self.index.hnsw.efSearch = int(ef)
            except Exception:
                pass
            t0 = time.perf_counter()
            _D, _I = self.index.search(xq_sample, k)
            t1 = time.perf_counter()
            avg_ms = (t1 - t0) * 1000.0 / float(xq_sample.shape[0])
            if avg_ms <= self.latency_ms_target:
                best_ef = ef
            else:
                break  # as ef increases, time generally increases

        # Set final ef
        try:
            self.index.hnsw.efSearch = int(best_ef)
        except Exception:
            pass
        return int(best_ef)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None:
            self._create_index()

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}) and dtype float32")
        xq = np.ascontiguousarray(xq)

        # Ensure threading setup
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        # Any last-minute index parameter tuning
        if isinstance(self.index, faiss.IndexHNSW) or isinstance(self.index, faiss.IndexHNSWFlat):
            if self.auto_tune:
                self._autotune_hnsw_ef(xq, k)
            else:
                ef = int(self._ef_search_user) if self._ef_search_user is not None else 500
                try:
                    self.index.hnsw.efSearch = ef
                except Exception:
                    pass
        elif isinstance(self.index, faiss.IndexIVF):
            # Set nprobe; if quantizer is HNSW, configure efSearch for the quantizer
            self.index.nprobe = max(1, int(self.nprobe))
            if isinstance(self.index.quantizer, faiss.IndexHNSW):
                try:
                    # efSearch for the quantizer proportional to nprobe
                    self.index.quantizer.hnsw.efSearch = max(64, min(1024, self.index.nprobe * 4))
                except Exception:
                    pass

        D, I = self.index.search(xq, k)

        # Ensure correct dtypes and shapes
        if not isinstance(D, np.ndarray):
            D = np.array(D)
        if not isinstance(I, np.ndarray):
            I = np.array(I)

        D = np.ascontiguousarray(D.astype(np.float32, copy=False))
        I = np.ascontiguousarray(I.astype(np.int64, copy=False))

        return D, I