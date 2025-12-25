import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        
        We use HNSW (Hierarchical Navigable Small World) graph which offers 
        excellent latency-recall trade-offs. 
        - HNSW32: M=32 links per node. This is robust for 128D vectors.
        - Flat: We store full float32 vectors. 1M vectors * 128 * 4 bytes = 512MB,
          which fits easily in the 16GB RAM constraint and avoids quantization errors.
        """
        self.dim = dim
        # Initialize HNSW index with M=32
        self.index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_L2)
        
        # Set efConstruction higher than default to build a higher quality graph.
        # This takes more time during add(), but allows for faster search() 
        # (lower efSearch) to achieve the same recall.
        # Time complexity of add() is not part of the score.
        self.index.hnsw.efConstruction = 120

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index and auto-tune search parameters.
        """
        # Keep track of the ID offset for the new vectors
        start_id = self.index.ntotal
        
        # Add vectors to the HNSW structure
        self.index.add(xb)
        
        # --- Auto-Tuning Strategy ---
        # The goal is to find the minimum `efSearch` that satisfies the recall constraint.
        # Lower `efSearch` results in lower latency (higher score).
        # We use "Self-Recall" (finding the vector itself) as a proxy for Query Recall.
        # We tune for ~96% Self-Recall to safely ensure >=80% Query Recall.
        
        # Skip tuning if the index is too small to be representative
        if self.index.ntotal < 1000:
            self.index.hnsw.efSearch = 32
            return

        n_avail = xb.shape[0]
        n_samples = 256  # Sufficient sample size for parameter estimation
        
        # Select sample vectors for tuning
        if n_avail > n_samples:
            # Use a fixed seed for deterministic behavior
            rng = np.random.RandomState(42)
            indices = rng.choice(n_avail, n_samples, replace=False)
            queries = xb[indices]
            gt_ids = start_id + indices
        else:
            # Use all available vectors if batch is small
            queries = xb
            gt_ids = start_id + np.arange(n_avail)
            
        # Candidate values for efSearch.
        # We start with very low values (fastest) and increase until recall is met.
        candidates = [8, 10, 12, 16, 20, 24, 32, 40, 50, 64, 80, 100, 128]
        
        # Target Self-Recall: 0.96 (heuristic buffer for 0.80 real recall)
        target_recall = 0.96
        best_ef = 128  # Fallback safe value
        
        # Test candidates
        for ef in candidates:
            self.index.hnsw.efSearch = ef
            
            # Search for the sample vectors themselves (k=1)
            D, I = self.index.search(queries, k=1)
            
            # Calculate recall (fraction of vectors finding themselves as NN)
            matches = (I.flatten() == gt_ids).sum()
            recall = matches / len(queries)
            
            if recall >= target_recall:
                best_ef = ef
                break
        
        # Apply the optimal parameter
        self.index.hnsw.efSearch = best_ef

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        # Faiss handles multithreading automatically using available CPUs (8 vCPUs)
        # for batch queries, ensuring high throughput.
        return self.index.search(xq, k)
