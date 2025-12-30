import numpy as np
import faiss
from typing import Tuple, List, Optional


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.nlist = int(kwargs.get("nlist", 16384))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.max_train_points = int(kwargs.get("max_train_points", 200000))
        self.min_train_points_per_centroid = int(kwargs.get("min_points_per_centroid", 5))

        # Build IVF-Flat with L2 metric
        self.quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(self.quantizer, self.dim, self.nlist, faiss.METRIC_L2)

        # Adjust clustering parameters to allow training on moderate sample sizes
        try:
            self.index.cp.min_points_per_centroid = max(1, self.min_train_points_per_centroid)
        except Exception:
            pass

        self.index.nprobe = self.nprobe

        # Buffers before training
        self._pending_add: List[np.ndarray] = []
        self._pending_count: int = 0

        # Training sample target: enough to cover centroids reasonably while staying within memory/time
        self._train_target = max(self.nlist * self.min_train_points_per_centroid, 100000)
        self._train_target = min(self._train_target, self.max_train_points)

        # Random generator for sampling
        self._rng = np.random.default_rng(12345)

    def _accumulate_pending(self, xb: np.ndarray) -> None:
        self._pending_add.append(xb)
        self._pending_count += xb.shape[0]

    def _sample_training_data(self) -> np.ndarray:
        total = self._pending_count
        if total <= 0:
            return np.empty((0, self.dim), dtype=np.float32)

        target = min(self._train_target, total)
        # Randomly sample indices across all pending arrays without concatenating everything
        # Build prefix sums to map global indices to array-local indices
        sizes = [arr.shape[0] for arr in self._pending_add]
        prefix = np.cumsum([0] + sizes)
        # Choose unique random global indices
        idxs = self._rng.choice(total, size=target, replace=False)
        idxs.sort()
        train_data = np.empty((target, self.dim), dtype=np.float32)

        # Map each chosen index to the appropriate array
        ai = 0  # array index
        offset = prefix[ai + 1]
        j = 0
        for t in range(target):
            gidx = idxs[t]
            while gidx >= offset:
                ai += 1
                offset = prefix[ai + 1]
            local_idx = gidx - prefix[ai]
            train_data[j] = self._pending_add[ai][local_idx]
            j += 1
        return train_data

    def _train_if_needed(self) -> None:
        if self.index.is_trained:
            return
        # Only train when we have enough pending data
        min_points = max(self.nlist * self.min_train_points_per_centroid, 50000)
        if self._pending_count < min_points:
            return
        train_data = self._sample_training_data()
        if train_data.shape[0] == 0:
            return
        # Ensure correct dtype/contiguity
        train_data = np.ascontiguousarray(train_data, dtype=np.float32)
        self.index.train(train_data)

        # After training, add all pending vectors
        for arr in self._pending_add:
            self.index.add(arr)
        self._pending_add.clear()
        self._pending_count = 0

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.shape[1] != self.dim:
            raise ValueError("Input dimension does not match index dimension")

        if not self.index.is_trained:
            self._accumulate_pending(xb)
            self._train_if_needed()
            # If still not trained (e.g., very small initial chunks), defer adding
            if self.index.is_trained:
                return
        else:
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.shape[1] != self.dim:
            raise ValueError("Query dimension does not match index dimension")

        # If somehow still not trained (e.g., only tiny adds), train on whatever we have
        if not self.index.is_trained and self._pending_count > 0:
            # Force training with whatever data is available (down to 1 point per centroid)
            try:
                self.index.cp.min_points_per_centroid = 1
            except Exception:
                pass
            train_data = self._sample_training_data()
            if train_data.shape[0] == 0:
                # Fallback: if still nothing, we cannot search; return empty
                nq = xq.shape[0]
                return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)
            train_data = np.ascontiguousarray(train_data, dtype=np.float32)
            self.index.train(train_data)
            for arr in self._pending_add:
                self.index.add(arr)
            self._pending_add.clear()
            self._pending_count = 0

        # Ensure at least some lists are probed
        self.index.nprobe = max(1, min(self.nprobe, self.nlist))

        D, I = self.index.search(xq, int(k))
        # Ensure correct dtypes
        D = np.ascontiguousarray(D, dtype=np.float32)
        I = np.ascontiguousarray(I, dtype=np.int64)
        return D, I