import numpy as np
import faiss
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        Strategy:
        - Use HNSW (Hierarchical Navigable Small World) graph for efficient approximate search.
        - Use Flat storage (IndexHNSWFlat) to store exact vectors. This avoids quantization 
          loss, ensuring we can meet the strict 95% recall requirement more easily than PQ.
        - Optimization focuses on tuning M and efSearch to balance recall and latency.
        """
        self.dim = dim
        
        # Configuration for SIFT1M (1M vectors, 128 dim)
        # M=32: Number of connections per node. Higher M improves recall at cost of speed/memory.
        # 32 is a robust sweet spot for 1M vectors to maintain high recall.
        self.M = kwargs.get('M', 32)
        
        # Initialize the Faiss index
        # IndexHNSWFlat wraps a flat index (exact distances) with an HNSW graph
        self.index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_L2)
        
        # efConstruction: Controls graph quality during build time.
        # Build time is not part of the score (only query latency is).
        # We use a high value (128) to build a high-quality graph.
        self.index.hnsw.efConstruction = kwargs.get('ef_construction', 128)
        
        # efSearch: Controls the size of the candidate list during search.
        # This is the primary knob for the Recall vs Latency trade-off.
        # For SIFT1M:
        # - efSearch=64 with M=32 typically yields ~98-99% recall.
        # - We set it to 80 to have a safety buffer above the 95% gate.
        # - Latency with efSearch=80 is typically < 1ms for batch queries on modern CPUs,
        #   well within the 7.7ms budget for max score.
        self.index.hnsw.efSearch = kwargs.get('ef_search', 80)
        
        # Note: Faiss automatically utilizes OpenMP for batch queries.
        # The environment's 8 vCPUs will be used effectively for the 10k query batch.

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        # Ensure array is C-contiguous for Faiss
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Ensure array is C-contiguous
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)
        
        # Perform batch search
        # Returns (distances, indices)
        # Distances are squared L2 because metric is METRIC_L2
        distances, indices = self.index.search(xq, k)
        
        return distances, indices