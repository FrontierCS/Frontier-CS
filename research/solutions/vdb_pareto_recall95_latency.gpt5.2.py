import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    raise ImportError("faiss is required for this solution") from e


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 64))
        self.train_size = int(kwargs.get("train_size", 100000))
        if self.train_size < self.nlist:
            self.train_size = self.nlist

        self.num_threads = int(kwargs.get("num_threads", 0)) or (os.cpu_count() or 1)
        self.num_threads = max(1, min(32, self.num_threads))

        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        quantizer = faiss.IndexFlatL2(self.dim)
        self.index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist, faiss.METRIC_L2)
        self.index.nprobe = self.nprobe

        self._pending = []
        self._pending_total = 0
        self._rng = np.random.default_rng(12345)

    def _as_float32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)
        if not x.flags["C_CONTIGUOUS"]:
            x = np.ascontiguousarray(x)
        return x

    def _gather_sample_from_pending(self, m: int) -> np.ndarray:
        total = self._pending_total
        if total <= 0:
            return np.empty((0, self.dim), dtype=np.float32)
        m = min(int(m), total)
        if m <= 0:
            return np.empty((0, self.dim), dtype=np.float32)

        idx = self._rng.choice(total, size=m, replace=False)
        idx.sort()

        out = np.empty((m, self.dim), dtype=np.float32)
        out_pos = 0
        base = 0
        for chunk in self._pending:
            n = chunk.shape[0]
            lo = np.searchsorted(idx, base, side="left")
            hi = np.searchsorted(idx, base + n, side="left")
            if hi > lo:
                sel = idx[lo:hi] - base
                out[out_pos : out_pos + sel.size] = chunk[sel]
                out_pos += sel.size
            base += n
            if out_pos >= m:
                break

        if out_pos != m:
            out = out[:out_pos]
        return out

    def _ensure_trained(self) -> None:
        if self.index.is_trained:
            return
        if self._pending_total <= 0:
            return
        train_x = self._gather_sample_from_pending(self.train_size)
        if train_x.shape[0] < self.nlist:
            # Faiss needs at least nlist training points; fall back to using all pending if possible
            # (still may fail if total < nlist, but that is an inherently invalid setup for IVF)
            train_x = self._gather_sample_from_pending(self._pending_total)
        train_x = self._as_float32_contig(train_x)
        self.index.train(train_x)
        for chunk in self._pending:
            self.index.add(chunk)
        self._pending.clear()
        self._pending_total = 0

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_float32_contig(xb)
        n = xb.shape[0]
        if n == 0:
            return

        if self.index.is_trained:
            self.index.add(xb)
            return

        # If we have no pending and this chunk is large enough, train directly from it to avoid buffering.
        if self._pending_total == 0 and n >= self.train_size:
            m = min(self.train_size, n)
            idx = self._rng.choice(n, size=m, replace=False)
            train_x = np.take(xb, idx, axis=0)
            train_x = self._as_float32_contig(train_x)
            self.index.train(train_x)
            self.index.add(xb)
            return

        self._pending.append(xb)
        self._pending_total += n

        if self._pending_total >= self.train_size:
            self._ensure_trained()

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            nq = int(xq.shape[0])
            return np.empty((nq, 0), dtype=np.float32), np.empty((nq, 0), dtype=np.int64)

        self._ensure_trained()

        xq = self._as_float32_contig(xq)
        if self.index.ntotal == 0:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        # Ensure current nprobe setting is applied (in case user mutated it via kwargs-like access)
        self.index.nprobe = self.nprobe

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I