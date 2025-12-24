import numpy as np
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall with low latency.
        Parameters tuned for SIFT1M to achieve >95% recall with <7.7ms latency.
        """
        self.dim = dim
        # HNSW parameters optimized for recall-first approach
        # M=32 provides good connectivity for recall, efSearch=64 ensures high accuracy
        # efConstruction=200 builds a high-quality graph for better recall
        self.M = kwargs.get('M', 32)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 64)
        
        # Initialize HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Enable efficient batch processing
        faiss.omp_set_num_threads(8)  # Use all 8 vCPUs for parallel processing

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        Uses HNSW's efficient incremental addition.
        """
        if not self.index.is_trained:
            self.index.train(xb[:min(10000, len(xb))])  # Train on subset
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors using HNSW with batch optimization.
        Returns distances and indices for all queries.
        """
        # Set efSearch parameter for this batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform the search (FAISS handles batching efficiently)
        distances, indices = self.index.search(xq, k)
        
        # FAISS returns squared L2 distances, convert to L2 for consistency
        distances = np.sqrt(np.maximum(distances, 0.0))
        
        return distances.astype(np.float32), indices.astype(np.int64)
