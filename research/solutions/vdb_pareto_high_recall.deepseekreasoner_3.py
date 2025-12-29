import numpy as np
import faiss
import time

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize HNSW index optimized for high recall within 7.7ms latency constraint.
        """
        self.dim = dim
        
        # HNSW parameters optimized for high recall with relaxed latency constraint
        # M=32 provides good connectivity for high recall
        # efConstruction=200 ensures high quality graph construction
        # efSearch can be tuned for recall-latency tradeoff
        self.M = kwargs.get('M', 32)
        self.ef_construction = kwargs.get('ef_construction', 200)
        self.ef_search = kwargs.get('ef_search', 800)  # High for max recall
        
        # Initialize HNSW index
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        
        # Store vectors for exact distance computation if needed
        self.xb = None
        self.is_trained = False

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        if self.xb is None:
            self.xb = xb.astype(np.float32)
        else:
            self.xb = np.vstack([self.xb, xb.astype(np.float32)])
        
        # Train index if not already trained
        if not self.is_trained:
            self.index.train(self.xb)
            self.is_trained = True
        
        # Add vectors in batches to avoid memory issues
        batch_size = 100000
        n_vectors = xb.shape[0]
        
        for i in range(0, n_vectors, batch_size):
            end_idx = min(i + batch_size, n_vectors)
            batch = xb[i:end_idx].astype(np.float32)
            self.index.add(batch)

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors with optimized batch processing.
        """
        # Ensure queries are float32
        xq = xq.astype(np.float32)
        
        # Set efSearch parameter (can be adjusted per query if needed)
        self.index.hnsw.efSearch = self.ef_search
        
        # For high recall, we use exact search for top candidates
        # First get more candidates than needed, then refine
        search_k = min(k * 4, 256)  # Get more candidates for refinement
        
        # Perform initial approximate search
        distances, indices = self.index.search(xq, search_k)
        
        # If k is 1, we can directly return the top result
        if k == 1:
            return distances[:, :1].astype(np.float32), indices[:, :1].astype(np.int64)
        
        # For k > 1, refine the results with exact distance computation
        # This ensures highest possible recall
        nq = xq.shape[0]
        final_distances = np.zeros((nq, k), dtype=np.float32)
        final_indices = np.zeros((nq, k), dtype=np.int64)
        
        # Compute exact distances for top candidates
        for i in range(nq):
            # Get the candidate vectors
            candidate_indices = indices[i, :search_k]
            candidate_vectors = self.xb[candidate_indices]
            
            # Compute exact L2 distances
            diff = xq[i] - candidate_vectors
            exact_dists = np.sum(diff * diff, axis=1)
            
            # Get top k exact results
            top_k_idx = np.argpartition(exact_dists, k)[:k]
            sorted_idx = top_k_idx[np.argsort(exact_dists[top_k_idx])]
            
            final_indices[i] = candidate_indices[sorted_idx]
            final_distances[i] = exact_dists[sorted_idx]
        
        return final_distances, final_indices