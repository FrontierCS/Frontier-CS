import numpy as np
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall within 7.7ms latency.
        Parameters tuned for SIFT1M (1M vectors, 128 dim) with batch queries.
        """
        # HNSW parameters optimized for recall with 7.7ms budget
        # M=64: high connectivity for better recall (default is 16-32)
        # efConstruction=200: thorough graph construction
        # efSearch=512: aggressive search for high recall
        # Using cosine similarity (IP) with normalized vectors for better accuracy
        self.dim = dim
        self.M = kwargs.get('M', 64)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 512)
        
        # Create inner product index for cosine similarity
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_INNER_PRODUCT)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Track if data is added (for normalization)
        self.data_added = False
        # Store original vectors for re-normalization during search
        self.vectors = None

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index with L2 normalization for cosine similarity.
        """
        # Store original vectors
        if self.vectors is None:
            self.vectors = xb.copy()
        else:
            self.vectors = np.vstack([self.vectors, xb])
        
        # L2 normalize for cosine similarity (inner product = cosine for unit vectors)
        xb_normalized = xb.copy()
        faiss.normalize_L2(xb_normalized)
        
        # Add to index
        self.index.add(xb_normalized)
        self.data_added = True

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors using HNSW with tuned parameters.
        Returns L2 distances (converted from inner product distances).
        """
        # Normalize query vectors for cosine similarity
        xq_normalized = xq.copy().astype(np.float32)
        faiss.normalize_L2(xq_normalized)
        
        # Set efSearch for this search
        current_ef_search = self.ef_search
        # Dynamic adjustment: increase efSearch if we have fewer queries in batch
        # to maintain consistent recall, but we're doing batch of 10K so use default
        self.index.hnsw.efSearch = current_ef_search
        
        # Search for k+5 neighbors to have some margin for L2 distance conversion
        search_k = min(k + 5, self.index.ntotal)
        distances_ip, indices = self.index.search(xq_normalized, search_k)
        
        # Convert inner product distances to L2 distances
        # For unit vectors: ||x - y||^2 = 2 - 2<x,y>
        # So L2 distance = sqrt(2 - 2*inner_product)
        # We'll compute L2 squared for efficiency (matches FAISS convention)
        distances_l2_squared = 2 - 2 * distances_ip
        
        # Get top k results
        if search_k > k:
            # Re-sort by L2 distance
            for i in range(len(indices)):
                if k < search_k:
                    # Get indices of k smallest L2 distances
                    top_k_idx = np.argpartition(distances_l2_squared[i], k)[:k]
                    # Sort these k indices
                    sorted_top_k = top_k_idx[np.argsort(distances_l2_squared[i][top_k_idx])]
                    indices[i, :k] = indices[i, sorted_top_k]
                    distances_l2_squared[i, :k] = distances_l2_squared[i, sorted_top_k]
        
        # Return L2 distances (squared) and indices
        return distances_l2_squared[:, :k].astype(np.float32), indices[:, :k].astype(np.int64)
