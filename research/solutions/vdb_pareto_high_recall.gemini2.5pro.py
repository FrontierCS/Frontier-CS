import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters for HNSW (M, ef_construction, ef_search)
        """
        self.dim = dim
        
        # Parameters are tuned for the High Recall Tier. The goal is to maximize recall@1
        # while staying under the t_max = 7.7ms latency constraint. The generous 2x latency
        # budget allows for a more thorough and accurate search compared to a balanced setting.

        # M: Number of neighbors per node in the HNSW graph. Higher M builds a denser,
        # higher-quality graph, leading to better recall. M=64 is a high value chosen
        # for this high-recall task.
        M = kwargs.get("M", 64)
        
        # efConstruction: A build-time parameter controlling the quality of the HNSW graph.
        # A higher value results in a better graph and thus higher search recall, at the
        # cost of a longer index build time. 500 is a high value that is feasible within
        # the 1-hour total evaluation time limit.
        ef_construction = kwargs.get("ef_construction", 500)
        
        # efSearch: A search-time parameter controlling the size of the dynamic candidate list.
        # This is the primary knob for tuning the speed vs. recall trade-off. A value of 104
        # is chosen as a safe but aggressive setting. It significantly increases search
        # thoroughness compared to typical baselines, aiming to use the extra latency budget
        # to surpass the 0.9914 recall target, while providing a safety margin to stay under
        # the 7.7ms limit on the evaluation hardware.
        ef_search = kwargs.get("ef_search", 104)

        # We use faiss.IndexHNSWFlat, which stores the full, uncompressed vectors.
        # This avoids recall loss from quantization (like Product Quantization) and is
        # feasible since the SIFT1M dataset (approx. 512MB) fits in the 16GB RAM.
        # The metric is set to L2 (Euclidean), as required by the problem.
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. This method can be called multiple times,
        and the FAISS HNSW index will handle cumulative additions.
        FAISS HNSW does not require a separate training step.
        """
        # The evaluator provides float32 numpy arrays, which is what FAISS expects.
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
        # The efSearch parameter set during initialization will be used for the search.
        # FAISS is highly optimized for batch queries, which is how the evaluator calls this method.
        distances, indices = self.index.search(xq, k)
        return distances, indices
