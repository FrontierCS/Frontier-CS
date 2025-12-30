import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Optional kwargs:
            - index_type: "ivfflat" (default) or "ivfpq"
            - nlist: number of IVF lists (default: 4096)
            - nprobe: number of probes at search time (default: 128)
            - train_size: number of vectors used for training (default: 100000)
            - m: number of PQ subquantizers (for ivfpq, default: 16)
            - nbits: bits per PQ subvector (for ivfpq, default: 8)
        """
        self.dim = int(dim)

        self.index_type = kwargs.get("index_type", "ivfflat").lower()
        if self.index_type not in ("ivfflat", "ivfpq"):
            self.index_type = "ivfflat"

        self.nlist = int(kwargs.get("nlist", 4096))
        if self.nlist <= 0:
            self.nlist = 4096

        self.nprobe = int(kwargs.get("nprobe", 128))
        if self.nprobe <= 0:
            self.nprobe = 128

        self.train_size = int(kwargs.get("train_size", 100000))
        if self.train_size <= 0:
            self.train_size = 100000

        # PQ-specific parameters (used only if index_type == "ivfpq")
        self.m = int(kwargs.get("m", 16))
        if self.m <= 0 or self.m > self.dim:
            self.m = 16
        self.nbits = int(kwargs.get("nbits", 8))
        if self.nbits <= 0 or self.nbits > 16:
            self.nbits = 8

        self.index = None  # faiss index (built lazily)
        self._xb = None    # accumulated database vectors (numpy array)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. Data is accumulated and the FAISS index
        is built lazily on the first call to search().
        """
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        xb = np.ascontiguousarray(xb, dtype=np.float32)

        if self._xb is None:
            # First batch: just keep a reference (no copy if already contiguous)
            self._xb = xb
        else:
            # Subsequent batches: concatenate
            self._xb = np.vstack((self._xb, xb))

    def _build_index(self) -> None:
        """
        Build and train the FAISS index from accumulated vectors.
        Called lazily on the first search().
        """
        if self.index is not None:
            return

        if self._xb is None or self._xb.size == 0:
            raise RuntimeError("No vectors have been added to the index.")

        xb_all = self._xb
        n, d = xb_all.shape
        if d != self.dim:
            raise ValueError(f"Expected dimension {self.dim}, got {d}")

        # Create quantizer and IVF index
        quantizer = faiss.IndexFlatL2(self.dim)

        if self.index_type == "ivfpq":
            # IVF with Product Quantization
            index = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist,
                                     self.m, self.nbits)
        else:
            # Default: IVF with full-precision vectors in lists
            index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        # Training
        n_train = min(self.train_size, n)
        if n_train < self.nlist:
            # Ensure we have at least nlist training vectors
            n_train = min(n, max(self.nlist, 2 * self.nlist))

        if n_train < self.nlist:
            # Fallback: if still not enough (tiny dataset), use all vectors
            train_x = xb_all
        else:
            if n_train == n:
                train_x = xb_all
            else:
                rs = np.random.RandomState(123)
                idx = rs.choice(n, size=n_train, replace=False)
                train_x = xb_all[idx]

        train_x = np.ascontiguousarray(train_x, dtype=np.float32)
        index.train(train_x)

        # Add all database vectors
        index.add(xb_all)

        # Set search-time parameters
        if hasattr(index, "nprobe"):
            index.nprobe = self.nprobe

        self.index = index
        # We can release the raw data; FAISS keeps its own copy
        self._xb = None

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if k <= 0:
            raise ValueError("k must be positive")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        if self.index is None:
            self._build_index()

        # Perform search using FAISS
        distances, indices = self.index.search(xq, k)

        # Ensure dtypes and shapes are as required
        distances = np.asarray(distances, dtype=np.float32)
        indices = np.asarray(indices, dtype=np.int64)

        return distances, indices