import os
from typing import Tuple
import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        **kwargs
    ):
        """
        Initialize the index for vectors of dimension `dim`.

        Optional kwargs:
            - algorithm: 'ivf_hnsw' (default) or 'hnsw_flat'
            - nlist: number of IVF lists (default 32768)
            - nprobe: number of probed lists at search time (default 512)
            - hnsw_m: HNSW neighbor parameter (default 32)
            - hnsw_ef_construction: HNSW efConstruction for building graph (default 200)
            - ef_search_coarse_factor: multiplier for coarse HNSW efSearch (default 1.2)
            - max_train_points: max number of vectors used for IVF training (default 400000)
            - seed: random seed for training sampling (default 123)
            - threads: int, FAISS OMP threads (default: os.cpu_count() or 8)
        """
        if faiss is None:
            raise RuntimeError("faiss is required for this solution")

        self.d = int(dim)
        self.algorithm = str(kwargs.get("algorithm", "ivf_hnsw")).lower()

        # IVF parameters
        self.nlist = int(kwargs.get("nlist", 32768))
        self.nprobe = int(kwargs.get("nprobe", 512))
        self.max_train_points = int(kwargs.get("max_train_points", 400000))

        # HNSW parameters
        self.hnsw_m = int(kwargs.get("hnsw_m", 32))
        self.hnsw_ef_construction = int(kwargs.get("hnsw_ef_construction", 200))
        self.ef_search_coarse_factor = float(kwargs.get("ef_search_coarse_factor", 1.2))

        # HNSW Flat params for alternative algorithm
        self.hnsw_ef_search = int(kwargs.get("ef_search", 400))
        self.hnsw_m_flat = int(kwargs.get("M", self.hnsw_m))
        self.hnsw_ef_construction_flat = int(kwargs.get("ef_construction", self.hnsw_ef_construction))

        self.seed = int(kwargs.get("seed", 123))

        # Threads
        self.threads = int(kwargs.get("threads", min(os.cpu_count() or 8, 8)))
        try:
            faiss.omp_set_num_threads(self.threads)
        except Exception:
            pass

        # Internal
        self.index = None
        self._ntotal = 0
        self._buffer = []
        self._buffer_size = 0
        self._trained = False
        self._rng = np.random.RandomState(self.seed)

        # For IVF: minimum number of points before training
        # ensure at least nlist samples
        self._min_train_points = max(self.nlist, 50000)

        # Metric
        self.metric = faiss.METRIC_L2

        # Pre-create index structure
        self._create_index()

    def _create_index(self):
        if self.algorithm == "hnsw_flat":
            # Hierarchical NSW over full vectors
            idx = faiss.IndexHNSWFlat(self.d, self.hnsw_m_flat)
            idx.hnsw.efConstruction = self.hnsw_ef_construction_flat
            idx.hnsw.efSearch = max(64, self.hnsw_ef_search)
            self.index = idx
            self._trained = True  # HNSWFlat does not require training
            return

        # Default: IVF-Flat with HNSW coarse quantizer
        quantizer = faiss.IndexHNSWFlat(self.d, self.hnsw_m)
        quantizer.hnsw.efConstruction = self.hnsw_ef_construction
        quantizer.hnsw.efSearch = max(64, int(self.nprobe * self.ef_search_coarse_factor))

        index = faiss.IndexIVFFlat(quantizer, self.d, self.nlist, self.metric)
        # Set nprobe; may be overridden in search
        index.nprobe = self.nprobe
        self.index = index
        self._trained = False

    def _finalize_training_if_needed(self):
        if self._trained:
            return
        if self.index is None:
            self._create_index()
        if self.index is None:
            raise RuntimeError("Index not created")

        # If not enough points to train, return (caller should add more or handle search later)
        if self._buffer_size < self._min_train_points:
            return

        # Prepare training set
        train_size = min(self.max_train_points, self._buffer_size)
        if train_size < self.nlist:
            # Not enough samples to train IVF properly; delay
            return

        xb_all = np.ascontiguousarray(np.vstack(self._buffer), dtype=np.float32)
        if train_size < xb_all.shape[0]:
            idxs = self._rng.choice(xb_all.shape[0], size=train_size, replace=False)
            xtrain = xb_all[idxs]
        else:
            xtrain = xb_all

        # Train IVF
        self.index.train(xtrain)
        self._trained = True

        # After training, add buffered data
        self.index.add(xb_all)
        self._ntotal += xb_all.shape[0]
        self._buffer = []
        self._buffer_size = 0

        # Ensure coarse HNSW efSearch is adequate
        if isinstance(self.index.quantizer, faiss.IndexHNSW):
            try:
                self.index.quantizer.hnsw.efSearch = max(
                    self.index.nprobe,
                    int(self.nprobe * self.ef_search_coarse_factor),
                    64
                )
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)
        if xb.shape[1] != self.d:
            raise ValueError("Input dimension does not match index dimension")

        if self.index is None:
            self._create_index()

        if self.algorithm == "hnsw_flat":
            # No training required
            self.index.add(xb)
            self._ntotal += xb.shape[0]
            return

        # IVF path
        if not self._trained:
            # Buffer until we have enough to train
            self._buffer.append(xb)
            self._buffer_size += xb.shape[0]
            # Attempt to train when sufficient data accumulated
            self._finalize_training_if_needed()
        else:
            # Already trained: add directly
            self.index.add(xb)
            self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        if self.index is None:
            self._create_index()

        # If IVF and not trained yet (e.g., add called with small segments), finalize training
        if self.algorithm != "hnsw_flat":
            if not self._trained:
                # Force training using whatever available (this is a fallback for small datasets)
                if self._buffer_size >= max(self.nlist, 1000):
                    self._finalize_training_if_needed()
                else:
                    # If still not enough, create a temporary Flat index for exact search on small data
                    # This ensures correctness in degenerate cases
                    if self._buffer_size == 0:
                        # No data; return empty results
                        nq = xq.shape[0]
                        D = np.full((nq, k), np.inf, dtype=np.float32)
                        I = np.full((nq, k), -1, dtype=np.int64)
                        return D, I
                    xb_all = np.ascontiguousarray(np.vstack(self._buffer), dtype=np.float32)
                    # Compute exact distances for small sets
                    # Using Faiss Flat for speed
                    flat = faiss.IndexFlatL2(self.d)
                    flat.add(xb_all)
                    D, I = flat.search(xq, k)
                    # Remap indices relative to added points
                    return D, I

            # Ensure IVF runtime params
            try:
                self.index.nprobe = self.nprobe
            except Exception:
                pass
            try:
                if isinstance(self.index.quantizer, faiss.IndexHNSW):
                    self.index.quantizer.hnsw.efSearch = max(
                        self.nprobe,
                        int(self.nprobe * self.ef_search_coarse_factor),
                        64
                    )
            except Exception:
                pass
        else:
            # HNSW Flat runtime params
            try:
                self.index.hnsw.efSearch = max(64, self.hnsw_ef_search)
            except Exception:
                pass

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes/shapes
        if not isinstance(D, np.ndarray):
            D = np.array(D)
        if not isinstance(I, np.ndarray):
            I = np.array(I)
        D = np.ascontiguousarray(D, dtype=np.float32)
        I = np.ascontiguousarray(I, dtype=np.int64)
        return D, I
