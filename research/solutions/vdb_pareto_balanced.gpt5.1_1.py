import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optional kwargs:
            - index_key: FAISS index factory string (default: "IVF4096,Flat")
            - nlist: Number of IVF lists (default: 4096 if not overridden via index_key)
            - nprobe: Number of probes at search time (default: 1024)
            - train_size: Number of vectors used for training IVF (default: 100000)
            - random_seed: Seed for training sampling (default: 123)
            - num_threads: Number of FAISS threads (default: faiss.omp_get_max_threads())
        """
        self.dim = dim

        # Parameters
        self.index_key = kwargs.get("index_key", None)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 1024))
        self.train_size = int(kwargs.get("train_size", 100000))
        self.random_seed = int(kwargs.get("random_seed", 123))

        # If index_key not provided, construct default based on nlist
        if self.index_key is None:
            self.index_key = f"IVF{self.nlist},Flat"

        # Configure FAISS threading
        num_threads = kwargs.get("num_threads", None)
        if num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass
        else:
            try:
                max_threads = faiss.omp_get_max_threads()
                faiss.omp_set_num_threads(max_threads)
            except Exception:
                pass

        # Create FAISS index via factory
        self.index = faiss.index_factory(self.dim, self.index_key, faiss.METRIC_L2)

        # If IVF index, set nprobe
        if isinstance(self.index, faiss.IndexIVF):
            self.index.nprobe = min(self.nprobe, self.index.nlist)

        # RNG for training sampling
        self._rng = np.random.default_rng(self.random_seed)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        if xb is None or xb.size == 0:
            return

        xb = np.ascontiguousarray(xb, dtype="float32")
        if xb.shape[1] != self.dim:
            raise ValueError(f"Expected vectors of dimension {self.dim}, got {xb.shape[1]}")

        # Train IVF-type indexes on first add, if needed
        if hasattr(self.index, "is_trained") and not self.index.is_trained:
            n_train = min(self.train_size, xb.shape[0])
            if n_train <= 0:
                raise ValueError("Training requires at least one vector")

            if xb.shape[0] > n_train:
                train_idx = self._rng.choice(xb.shape[0], size=n_train, replace=False)
                x_train = xb[train_idx]
            else:
                x_train = xb

            self.index.train(x_train)

        # For IVF indexes, ensure nprobe is set (could be reset externally)
        if isinstance(self.index, faiss.IndexIVF):
            self.index.nprobe = min(self.nprobe, self.index.nlist)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if xq is None or xq.size == 0:
            nq = 0 if xq is None else xq.shape[0]
            return (
                np.empty((nq, k), dtype="float32"),
                np.empty((nq, k), dtype="int64"),
            )

        xq = np.ascontiguousarray(xq, dtype="float32")
        if xq.shape[1] != self.dim:
            raise ValueError(f"Expected query vectors of dimension {self.dim}, got {xq.shape[1]}")

        # Handle empty index
        if self.index is None or self.index.ntotal == 0:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype="float32")
            I = np.full((nq, k), -1, dtype="int64")
            return D, I

        # Ensure IVF probing parameter is set
        if isinstance(self.index, faiss.IndexIVF):
            self.index.nprobe = min(self.nprobe, self.index.nlist)

        D, I = self.index.search(xq, k)
        # Ensure correct dtypes
        D = np.asarray(D, dtype="float32")
        I = np.asarray(I, dtype="int64")
        return D, I
