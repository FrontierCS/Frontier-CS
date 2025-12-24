import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Optional kwargs:
            nlist: number of IVF clusters (default: 4096)
            nprobe: number of clusters to probe at search time (default: 256)
            max_train_points: max number of points used for IVF training (default: 100000)
            num_threads: number of FAISS threads (default: leave FAISS default)
        """
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 256))
        self.max_train_points = int(kwargs.get("max_train_points", 100000))

        num_threads = kwargs.get("num_threads", None)
        if num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass

        # Build IVF-Flat index (L2 metric)
        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None or xb.size == 0:
            return

        xb = np.ascontiguousarray(xb, dtype="float32")

        if not self.index.is_trained:
            # Train IVF with a subset of xb (or all if smaller)
            n_train = min(self.max_train_points, xb.shape[0])
            if xb.shape[0] > n_train:
                rng = np.random.default_rng(123)
                train_idx = rng.choice(xb.shape[0], size=n_train, replace=False)
                train_data = xb[train_idx]
            else:
                train_data = xb
            self.index.train(train_data)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        xq = np.ascontiguousarray(xq, dtype="float32")
        nq = xq.shape[0]

        if not self.index.is_trained or self.index.ntotal == 0:
            distances = np.empty((nq, k), dtype="float32")
            indices = np.full((nq, k), -1, dtype="int64")
            return distances, indices

        D, I = self.index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype("float32", copy=False)
        if I.dtype != np.int64:
            I = I.astype("int64", copy=False)

        return D, I
