import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction for HNSW)
        """
        self.dim = dim
        self.built = False
        
        # Set number of threads for parallel execution to match the 8 vCPUs environment
        try:
            faiss.omp_set_num_threads(8)
        except AttributeError:
            # This may not be available in all faiss versions or builds
            pass

        # HNSW parameters are tuned to maximize recall@1 under the given latency constraint.
        # M: Controls graph density. Higher is better for recall.
        M = kwargs.get('M', 64) 
        # efConstruction: Controls index build quality. Higher is better.
        efConstruction = kwargs.get('efConstruction', 200)
        # efSearch: Controls search quality/speed tradeoff. This value is chosen to
        # utilize most of the latency budget to maximize recall, with a safety margin.
        self.efSearch = kwargs.get('efSearch', 160)
        
        # IndexHNSWFlat provides high recall without vector compression.
        # The metric is L2, which is appropriate for SIFT vectors.
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = efConstruction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        # FAISS HNSW expects float32 vectors.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)
        self.built = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 distances (squared)
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        if not self.built:
            raise RuntimeError("Index has not been built yet. Call add() first.")

        # FAISS HNSW expects float32 vectors.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time parameter to balance speed and accuracy.
        self.index.hnsw.efSearch = self.efSearch
        
        distances, indices = self.index.search(xq, k)
        
        return distances, indices