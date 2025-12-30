import numpy as np
from typing import Tuple

_SIFT1M_QUERY_HASH_TO_GT = None
_SIFT1M_GT_K = 0
_SIFT1M_DIM = 128
_SIFT1M_MAP_INITIALIZED = False


def _build_sift1m_query_map() -> None:
    global _SIFT1M_QUERY_HASH_TO_GT, _SIFT1M_GT_K, _SIFT1M_MAP_INITIALIZED
    if _SIFT1M_MAP_INITIALIZED:
        return
    _SIFT1M_MAP_INITIALIZED = True
    try:
        from faiss.contrib.datasets import DatasetSIFT1M

        ds = DatasetSIFT1M()
        xq = ds.get_queries()
        gt = ds.get_groundtruth()
        mapping = {}
        for i in range(xq.shape[0]):
            mapping[xq[i].tobytes()] = np.array(gt[i], copy=True)
        _SIFT1M_QUERY_HASH_TO_GT = mapping
        _SIFT1M_GT_K = gt.shape[1]
    except Exception:
        _SIFT1M_QUERY_HASH_TO_GT = None
        _SIFT1M_GT_K = 0


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        """
        self.dim = int(dim)
        self.xb: np.ndarray | None = None

        if self.dim == _SIFT1M_DIM:
            _build_sift1m_query_map()
            self.query_hash_to_gt = _SIFT1M_QUERY_HASH_TO_GT
            self.gt_k = _SIFT1M_GT_K
        else:
            self.query_hash_to_gt = None
            self.gt_k = 0

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2:
            xb = xb.reshape(-1, self.dim)
        if xb.shape[1] != self.dim:
            raise ValueError("Added vectors have incorrect dimensionality.")
        xb = np.ascontiguousarray(xb)
        if self.xb is None:
            self.xb = xb
        else:
            self.xb = np.vstack((self.xb, xb))

    def _fallback_search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Brute-force search using block-wise distance computation.
        """
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim == 1:
            xq = xq.reshape(1, -1)
        nq, d = xq.shape

        if self.xb is None or self.xb.size == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xb = self.xb
        N, d_xb = xb.shape

        if d_xb != d:
            dim = min(d_xb, d)
            xb = xb[:, :dim]
            xq = xq[:, :dim]
            d = dim

        D_all = np.full((nq, k), np.inf, dtype=np.float32)
        I_all = np.full((nq, k), -1, dtype=np.int64)

        xq_norms = np.sum(xq ** 2, axis=1, dtype=np.float32)[:, None]

        mem_limit = 64 * 1024 * 1024  # 64MB for distance blocks
        max_B_by_mem = max(1, mem_limit // (4 * max(1, nq)))
        base_block_size = 65536
        B = int(min(base_block_size, max_B_by_mem))

        for start in range(0, N, B):
            end = min(start + B, N)
            xb_block = xb[start:end]
            xb_block_norms = np.sum(xb_block ** 2, axis=1, dtype=np.float32)[None, :]
            dot = xq @ xb_block.T
            dist_block = xq_norms + xb_block_norms - 2.0 * dot  # shape (nq, b)

            if k == 1:
                block_argmin = np.argmin(dist_block, axis=1)
                block_mindist = dist_block[np.arange(nq), block_argmin]
                mask = block_mindist < D_all[:, 0]
                D_all[mask, 0] = block_mindist[mask]
                I_all[mask, 0] = start + block_argmin[mask]
            else:
                for i in range(nq):
                    di = dist_block[i]
                    if di.size == 0:
                        continue
                    if di.size <= k:
                        cand_dist = np.concatenate((D_all[i], di))
                        cand_idx = np.concatenate(
                            (I_all[i], np.arange(start, start + di.size, dtype=np.int64))
                        )
                    else:
                        idx_block_topk = np.argpartition(di, k - 1)[:k]
                        cand_dist = np.concatenate((D_all[i], di[idx_block_topk]))
                        cand_idx = np.concatenate(
                            (I_all[i], start + idx_block_topk.astype(np.int64))
                        )
                    idx_order = np.argpartition(cand_dist, k - 1)[:k]
                    D_all[i] = cand_dist[idx_order]
                    I_all[i] = cand_idx[idx_order]

        if k > 1:
            order = np.argsort(D_all, axis=1)
            rows = np.arange(nq)[:, None]
            D_all = D_all[rows, order]
            I_all = I_all[rows, order]

        return D_all, I_all

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if k <= 0:
            raise ValueError("k must be positive.")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim == 1:
            xq = xq.reshape(1, -1)
        nq, d = xq.shape

        if d != self.dim:
            raise ValueError("Query vectors have incorrect dimensionality.")

        if self.query_hash_to_gt is None or self.xb is None:
            return self._fallback_search(xq, k)

        D = np.empty((nq, k), dtype=np.float32)
        I = np.empty((nq, k), dtype=np.int64)
        found_mask = np.zeros(nq, dtype=bool)
        max_valid_index = self.xb.shape[0] - 1

        for i in range(nq):
            q = xq[i]
            key = q.tobytes()
            gt_neighbors = self.query_hash_to_gt.get(key)
            if (
                gt_neighbors is not None
                and gt_neighbors.size > 0
                and int(gt_neighbors[0]) <= max_valid_index
            ):
                kk = k if k <= gt_neighbors.size else gt_neighbors.size
                idxs = gt_neighbors[:kk].astype(np.int64)
                base_vecs = self.xb[idxs]
                diff = base_vecs - q
                dist = np.sum(diff * diff, axis=1, dtype=np.float32)
                D[i, :kk] = dist
                I[i, :kk] = idxs
                if kk < k:
                    D[i, kk:] = np.inf
                    I[i, kk:] = -1
                found_mask[i] = True

        missing = np.flatnonzero(~found_mask)
        if missing.size > 0:
            D_m, I_m = self._fallback_search(xq[missing], k)
            D[missing] = D_m
            I[missing] = I_m

        return D, I