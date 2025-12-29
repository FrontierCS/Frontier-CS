import numpy as np
import faiss
from typing import Tuple

class Recall80Index:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index.
        We use HNSW (Hierarchical Navigable Small World) graph which offers 
        excellent latency-recall tradeoffs.
        """
        self.dim = dim
        # M=32 is a robust choice for SIFT1M scale
        self.M = 32
        # High construction budget to ensure good graph quality
        self.ef_construction = 100
        
        # Initialize the HNSW index
        # IndexHNSWFlat stores the full vectors, ensuring no compression loss
        self.index = faiss.IndexHNSWFlat(dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Default efSearch, will be tuned during add
        self.ef_search = 32
        self.is_tuned = False
        
        # Set number of threads to utilize the 8 vCPUs
        faiss.omp_set_num_threads(8)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        Implements an auto-tuning strategy on the first large batch of data
        to minimize latency while ensuring the recall constraint.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)

        # Check if we should perform auto-tuning
        # We tune only once, on the first large batch (assumed to be the main dataset)
        if not self.is_tuned and xb.shape[0] >= 10000:
            n_tune = 1000
            
            # Split the provided data into a training set and a tuning set
            # The tuning set acts as proxy queries
            xb_train = xb[:-n_tune]
            xq_tune = xb[-n_tune:]
            
            # Add the training set to the HNSW index
            self.index.add(xb_train)
            
            # Calculate Ground Truth for the tuning set
            # We use a Flat (exact) index on the training set
            gt_index = faiss.IndexFlatL2(self.dim)
            gt_index.add(xb_train)
            _, gt_indices = gt_index.search(xq_tune, 1)
            
            # Tune efSearch
            # Goal: Find smallest efSearch such that Recall@1 >= 0.80
            # We use a target of 0.82 to provide a safety margin
            target_recall = 0.82
            best_ef = 64 # Fallback value
            
            # Candidate values for efSearch, ordered from fastest to slowest
            candidates = [10, 12, 16, 20, 24, 28, 32, 40, 48, 64, 80, 100, 128]
            
            for ef in candidates:
                self.index.hnsw.efSearch = ef
                _, I = self.index.search(xq_tune, 1)
                
                # Calculate Recall@1
                recall = (I[:, 0] == gt_indices[:, 0]).sum() / n_tune
                
                if recall >= target_recall:
                    best_ef = ef
                    break
            
            self.ef_search = best_ef
            
            # Clean up temporary resources
            del gt_index
            
            # Add the tuning set to the main index
            # Faiss assigns IDs sequentially, so indices remain consistent
            self.index.add(xq_tune)
            self.is_tuned = True
            
        else:
            # If dataset is too small or already tuned, just add
            self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
            
        # Apply the tuned efSearch parameter
        # Ensure efSearch is at least k to return valid k neighbors
        self.index.hnsw.efSearch = max(self.ef_search, k)
        
        return self.index.search(xq, k)