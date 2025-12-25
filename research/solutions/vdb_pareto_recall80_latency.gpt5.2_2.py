import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 4096))
        self.nprobe = int(kwargs.get("nprobe", 4))
        self.m = int(kwargs.get("m", 16))
        self.nbits = int(kwargs.get("nbits", 8))
        self.opq = bool(kwargs.get("opq", True))
        self.train_size = int(kwargs.get("train_size", 100000))
        self.fast_scan = bool(kwargs.get("fast_scan", False))
        self.threads = int(kwargs.get("threads", min(8, (os.cpu_count() or 8))))

        if faiss is None:
            self._fallback_xb = None
            return

        faiss.omp_set_num_threads(self.threads)

        quantizer = faiss.IndexFlatL2(self.dim)

        if self.fast_scan:
            try:
                ivf = faiss.IndexIVFPQFastScan(quantizer, self.dim, self.nlist, self.m, self.nbits)
            except Exception:
                ivf = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)
        else:
            ivf = faiss.IndexIVFPQ(quantizer, self.dim, self.nlist, self.m, self.nbits)

        try:
            ivf.use_precomputed_table = 1
        except Exception:
            pass

        if self.opq:
            opq = faiss.OPQMatrix(self.dim, self.m)
            try:
                opq.niter = int(kwargs.get("opq_niter", 10))
            except Exception:
                pass
            index = faiss.IndexPreTransform(opq, ivf)
        else:
            index = ivf

        self.index = index
        self._set_nprobe(self.nprobe)

    def _as_float32_contig(self, x: np.ndarray) -> np.ndarray:
        if x.dtype != np.float32 or not x.flags["C_CONTIGUOUS"]:
            return np.ascontiguousarray(x, dtype=np.float32)
        return x

    def _get_ivf(self):
        if faiss is None:
            return None
        idx = self.index
        try:
            while isinstance(idx, faiss.IndexPreTransform):
                idx = idx.index
        except Exception:
            pass
        try:
            idx = faiss.downcast_index(idx)
        except Exception:
            pass
        return idx

    def _set_nprobe(self, nprobe: int):
        if faiss is None:
            return
        ivf = self._get_ivf()
        if ivf is not None and hasattr(ivf, "nprobe"):
            ivf.nprobe = int(nprobe)

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_float32_contig(xb)

        if faiss is None:
            if self._fallback_xb is None:
                self._fallback_xb = xb.copy()
            else:
                self._fallback_xb = np.vstack((self._fallback_xb, xb))
            return

        if not self.index.is_trained:
            ts = min(self.train_size, xb.shape[0])
            train_x = xb[:ts]
            self.index.train(train_x)
            self._set_nprobe(self.nprobe)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        xq = self._as_float32_contig(xq)

        if faiss is None:
            xb = self._fallback_xb
            if xb is None or xb.shape[0] == 0:
                nq = xq.shape[0]
                return (np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64))
            # fallback brute force (slow, only for environments without faiss)
            xq2 = (xq * xq).sum(axis=1, keepdims=True)
            xb2 = (xb * xb).sum(axis=1, keepdims=True).T
            dist = xq2 + xb2 - 2.0 * (xq @ xb.T)
            idx = np.argpartition(dist, kth=min(k - 1, dist.shape[1] - 1), axis=1)[:, :k]
            dsel = dist[np.arange(dist.shape[0])[:, None], idx]
            order = np.argsort(dsel, axis=1)
            I = idx[np.arange(idx.shape[0])[:, None], order].astype(np.int64, copy=False)
            D = dsel[np.arange(dsel.shape[0])[:, None], order].astype(np.float32, copy=False)
            return D, I

        self._set_nprobe(self.nprobe)
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I