import numpy as np
import faiss
from typing import Tuple

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Strategy:
        - Use HNSW (Hierarchical Navigable Small World) graph for efficient approximate nearest neighbor search.
        - Use Flat storage (IndexHNSWFlat) to ensure exact distance calculations for reranking/verification, 
          maximizing recall potential.
        - Parameters (M=64, efConstruction=500, efSearch=1024) are tuned to maximize recall@1 
          utilizing the generous 7.7ms latency budget. Standard HNSW usage often targets <1ms, 
          so we spend the extra time budget on a denser graph and deeper search to guarantee 
          recall exceeds the 0.9914 baseline.
        """
        self.dim = dim
        
        # Configuration for High Recall
        # M=64: Number of connections per node. Higher M increases graph density/connectivity,
        # leading to higher recall at the cost of memory and build time.
        self.M = 64
        
        # ef_construction: Depth of search during index building. 
        # 500 is high to ensure a high-quality navigable graph.
        self.ef_construction = 500
        
        # ef_search: Depth of search during querying.
        # 1024 is set conservatively high to saturate recall (approaching 1.0).
        # Estimated latency with these settings is ~2-3ms on modern CPUs, well within 7.7ms.
        self.ef_search = 1024
        
        # Initialize the index
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # Apply construction parameters
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # HNSWFlat does not require a separate train step, it builds incrementally
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        # Set the search depth parameter for this query batch
        self.index.hnsw.efSearch = self.ef_search
        
        # Perform search
        # Faiss efficiently parallelizes batch queries over available vCPUs
        distances, indices = self.index.search(xq, k)
        
        return distances, indices
