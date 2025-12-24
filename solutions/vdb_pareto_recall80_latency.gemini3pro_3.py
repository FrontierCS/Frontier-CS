import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Using HNSW (Hierarchical Navigable Small World) graph which offers 
        excellent recall/latency trade-offs.
        """
        self.dim = dim
        
        # M=32 is a robust setting for SIFT1M (128d) to ensure high recall capability
        self.M = 32
        
        # Initialize HNSW index with L2 metric
        # IndexHNSWFlat stores full vectors, ensuring accurate distance calculations
        # which is crucial for maximizing Recall@1 with minimal search depth.
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # Construction parameters:
        # efConstruction controls the quality of the graph build.
        # Setting this high (e.g., 128) takes longer to build but results in a 
        # better graph structure, allowing for faster search at a given recall.
        self.index.hnsw.efConstruction = 128
        
        # Search parameters:
        # efSearch controls the size of the dynamic candidate list during search.
        # We need Recall@1 >= 0.80.
        # Based on SIFT1M characteristics, efSearch=20 with M=32 typically yields 
        # Recall@1 between 0.85 and 0.90, while being extremely fast (<< 0.6ms).
        # We choose 20 to comfortably clear the 0.80 recall gate while minimizing latency.
        self.ef_search = 20

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Faiss requires C-contiguous float32 arrays
        if not xb.flags['C_CONTIGUOUS'] or xb.dtype != np.float32:
            xb = np.ascontiguousarray(xb, dtype=np.float32)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure query vectors are C-contiguous float32
        if not xq.flags['C_CONTIGUOUS'] or xq.dtype != np.float32:
            xq = np.ascontiguousarray(xq, dtype=np.float32)
            
        # Set the search-time parameter
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
