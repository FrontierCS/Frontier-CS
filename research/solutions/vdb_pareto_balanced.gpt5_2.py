import os
import numpy as np

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        # Parameters with robust defaults geared for high recall under latency constraint
        self.nlist = int(kwargs.get("nlist", 8192))
        self.M = int(kwargs.get("M", 16))  # PQ subquantizers
        self.nbits = int(kwargs.get("nbits", 8))  # bits per code
        self.nprobe = int(kwargs.get("nprobe", 160))  # probe lists at search
        self.k_factor = float(kwargs.get("k_factor", 128.0))  # refinement candidate multiplier
        self.training_samples = int(kwargs.get("training_samples", 250000))
        self.use_opq = bool(kwargs.get("use_opq", True))
        self.random_seed = int(kwargs.get("seed", 123))
        self.threads = int(kwargs.get("threads", max(1, min(os.cpu_count() or 8, 16))))

        self._xb_size = 0
        self._built = False
        self._index = None  # final searchable index (may be a wrapper)
        self._base_index = None  # base structure (IVFPQ or similar)

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.threads)
            except Exception:
                pass

    def _ensure_faiss(self):
        if faiss is None:
            raise RuntimeError("FAISS is required for this index implementation.")

    def _build_index(self, train_data: np.ndarray):
        self._ensure_faiss()

        # Coarse quantizer
        quantizer = faiss.IndexFlatL2(self.dim)

        # IVFPQ with residual encoding
        ivfpq = faiss.IndexIVFPQ(
            quantizer,
            self.dim,
            self.nlist,
            self.M,
            self.nbits,
        )
        ivfpq.by_residual = True

        # OPQ pre-transform to improve PQ accuracy
        if self.use_opq:
            opq = faiss.OPQMatrix(self.dim, self.M)
            opq.niter = 25
            base_index = faiss.IndexPreTransform(opq, ivfpq)
        else:
            base_index = ivfpq

        # Train index
        if not base_index.is_trained:
            base_index.train(train_data)

        # Wrap with refinement to compute exact distances on shortlist
        refine = faiss.IndexRefineFlat(base_index)
        refine.k_factor = self.k_factor

        # Set nprobe through ParameterSpace to handle composite indices
        ps = faiss.ParameterSpace()
        ps.set_index_parameter(refine, "nprobe", self.nprobe)

        self._base_index = base_index
        self._index = refine
        self._built = True

    def add(self, xb: np.ndarray) -> None:
        self._ensure_faiss()
        if not isinstance(xb, np.ndarray):
            xb = np.asarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        assert xb.shape[1] == self.dim, "xb dimension mismatch"

        # Build and train on first call
        if not self._built:
            # Sample for training
            n_train = min(self.training_samples, xb.shape[0])
            if n_train == xb.shape[0]:
                train_data = xb
            else:
                rng = np.random.RandomState(self.random_seed)
                perm = rng.permutation(xb.shape[0])[:n_train]
                train_data = xb[perm].copy()
            self._build_index(train_data)

        # Add data to index (through wrapper to handle bookkeeping)
        self._index.add(xb)
        self._xb_size += xb.shape[0]

    def search(self, xq: np.ndarray, k: int):
        self._ensure_faiss()
        if not isinstance(xq, np.ndarray):
            xq = np.asarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        assert xq.shape[1] == self.dim, "xq dimension mismatch"
        if not self._built or self._xb_size == 0:
            # Return empty results if no data added
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), -np.ones((nq, k), dtype=np.int64)

        # Batch search
        D, I = self._index.search(xq, k)
        # Ensure output types and shapes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I