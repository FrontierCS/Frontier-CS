import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for SIFT1M with parameters optimized for
        the Recall80 latency tier (recall >= 0.80, minimize latency).
        
        Strategy:
        - Use IndexIVFFlat for high-throughput batch search.
        - nlist=4096: Fine-grained partitioning (avg cluster size ~244).
        - nprobe=32: Scans ~0.8% of the dataset (~7800 vectors).
          This ensures recall > 0.90 (safely above 0.80 gate) while keeping 
          computation well within the 0.6ms average latency budget (estimated <0.05ms).
        """
        self.dim = dim
        self.nlist = 4096
        self.nprobe = 32
        
        # Coarse quantizer (flat L2)
        self.quantizer = faiss.IndexFlatL2(dim)
        # Inverted file index with full vectors (no compression/PQ to maximize recall speed trade-off)
        self.index = faiss.IndexIVFFlat(self.quantizer, dim, self.nlist, faiss.METRIC_L2)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index. Trains the quantizer if necessary.
        """
        # Ensure float32 (Faiss requirement)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
            
        # Train on the data if not yet trained
        # For SIFT1M (1M vectors), training on the full dataset is efficient
        if not self.index.is_trained:
            self.index.train(xb)
            
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Set nprobe for the search
        self.index.nprobe = self.nprobe
        
        # Perform search
        D, I = self.index.search(xq, k)
        return D, I