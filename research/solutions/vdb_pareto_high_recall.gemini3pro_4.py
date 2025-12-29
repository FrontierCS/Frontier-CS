import numpy as np
import faiss

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for the High Recall Tier.
        
        Strategy:
        - Use HNSW (Hierarchical Navigable Small World) graph which offers excellent recall-latency tradeoffs.
        - The 7.7ms latency budget is generous for SIFT1M on modern CPUs.
        - We prioritize recall by using a dense graph (M=64) and a deep search (ef_search=512).
        - This configuration typically yields recall > 0.998, comfortably exceeding the 0.9914 baseline,
          while remaining well under the 7.7ms limit (typically < 2-3ms).
        """
        self.dim = dim
        
        # HNSW Configuration
        # M=64: Number of connections per node. Higher M = better recall, higher memory/construction cost.
        # We can afford the extra cost here to guarantee the recall threshold.
        M = 64
        
        # Initialize the index
        # IndexHNSWFlat stores raw vectors (Flat) and uses HNSW for navigation.
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        
        # Construction parameter
        # efConstruction: Depth of search during graph construction. 
        # Higher = better graph quality.
        self.index.hnsw.efConstruction = 256
        
        # Runtime search parameter
        # efSearch: Depth of search during query.
        # Setting this to 512 ensures we explore a large portion of the graph to maximize recall.
        self.ef_search = 512
        
        # Threading optimization
        # The environment provides 8 vCPUs. Explicitly setting this ensures efficient batch processing.
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the HNSW index.
        """
        # Faiss requires C-contiguous arrays for optimal performance
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> tuple:
        """
        Search for k nearest neighbors.
        """
        # Set the search depth for this query batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Ensure query array is contiguous
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
            
        # Perform search
        # Returns: (distances, indices)
        return self.index.search(xq, k)