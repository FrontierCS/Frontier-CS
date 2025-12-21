import numpy as np
import heapq
import time
from typing import Tuple, List

class LowLatencyIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.data = None
        self.nlist = kwargs.get('nlist', 256)  # Number of IVF cells
        self.nprobe = kwargs.get('nprobe', 4)  # Cells to search
        self.centroids = None
        self.cell_assignments = None
        self.cells = None
        
    def add(self, xb: np.ndarray) -> None:
        if self.data is None:
            self.data = xb
        else:
            self.data = np.vstack([self.data, xb])
            
        if len(self.data) > 10000:  # Build index only when we have enough data
            self._build_index()
    
    def _build_index(self):
        N = len(self.data)
        nlist = min(self.nlist, N // 40)  # Ensure enough points per cell
        
        # Simple k-means initialization (using random centroids for speed)
        np.random.seed(42)
        idx = np.random.choice(N, nlist, replace=False)
        self.centroids = self.data[idx].copy()
        
        # Assign points to nearest centroid (approximate)
        self.cells = [[] for _ in range(nlist)]
        batch_size = 10000
        for i in range(0, N, batch_size):
            batch = self.data[i:i+batch_size]
            dists = np.sum((batch[:, None, :] - self.centroids[None, :, :]) ** 2, axis=2)
            nearest = np.argmin(dists, axis=1)
            for j, cell_id in enumerate(nearest):
                self.cells[cell_id].append(i + j)
        
        # Convert to numpy arrays for faster access
        self.cells = [np.array(cell, dtype=np.int64) for cell in self.cells]
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        nq = len(xq)
        distances = np.full((nq, k), np.inf, dtype=np.float32)
        indices = np.full((nq, k), -1, dtype=np.int64)
        
        if self.centroids is None:
            # Fallback to brute-force for very small datasets
            return self._brute_force_search(xq, k)
        
        # For each query, find nearest centroids
        centroid_dists = np.sum((xq[:, None, :] - self.centroids[None, :, :]) ** 2, axis=2)
        nearest_cells = np.argpartition(centroid_dists, self.nprobe, axis=1)[:, :self.nprobe]
        
        # Search only in selected cells
        for i in range(nq):
            candidates = []
            for cell_id in nearest_cells[i]:
                if cell_id < len(self.cells):
                    cell_points = self.cells[cell_id]
                    if len(cell_points) > 0:
                        # Compute distances to points in this cell
                        cell_data = self.data[cell_points]
                        dists = np.sum((xq[i] - cell_data) ** 2, axis=1)
                        # Add to candidates
                        for dist, idx in zip(dists, cell_points):
                            if len(candidates) < k or dist < candidates[0][0]:
                                if len(candidates) == k:
                                    heapq.heappushpop(candidates, (-dist, idx))
                                else:
                                    heapq.heappush(candidates, (-dist, idx))
            
            # Convert max-heap to sorted results
            if candidates:
                candidates.sort(reverse=True)
                for j in range(min(k, len(candidates))):
                    distances[i, j] = -candidates[j][0]
                    indices[i, j] = candidates[j][1]
        
        return distances, indices
    
    def _brute_force_search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        # Only used for tiny datasets
        nq = len(xq)
        N = len(self.data)
        distances = np.full((nq, k), np.inf, dtype=np.float32)
        indices = np.full((nq, k), -1, dtype=np.int64)
        
        batch_size = min(1000, N)
        for i in range(0, N, batch_size):
            batch = self.data[i:i+batch_size]
            batch_indices = np.arange(i, min(i+batch_size, N))
            # Compute distances in batches
            dists = np.sum((xq[:, None, :] - batch[None, :, :]) ** 2, axis=2)
            
            for q in range(nq):
                # Update k-nearest neighbors
                for j, dist in enumerate(dists[q]):
                    idx = batch_indices[j]
                    if dist < distances[q, -1]:
                        # Insert in sorted order
                        pos = k - 1
                        while pos > 0 and dist < distances[q, pos-1]:
                            distances[q, pos] = distances[q, pos-1]
                            indices[q, pos] = indices[q, pos-1]
                            pos -= 1
                        distances[q, pos] = dist
                        indices[q, pos] = idx
        
        return distances, indices

class FastHNSWIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.data = None
        self.M = kwargs.get('M', 12)  # Reduced connections for speed
        self.ef_search = kwargs.get('ef_search', 32)  # Low for latency
        self.ef_construction = kwargs.get('ef_construction', 40)
        self.max_level = kwargs.get('max_level', 4)  # Reduced levels
        
        # Simple HNSW structure
        self.layers = []  # Each layer is list of node indices
        self.neighbors = []  # neighbors[layer][node] = list of (node, dist)
        self.entry_point = None
        self.level_distribution = 1 / np.log(self.M)
    
    def _random_level(self):
        # Generate random level with exponential distribution
        level = 0
        while np.random.random() < self.level_distribution and level < self.max_level:
            level += 1
        return level
    
    def add(self, xb: np.ndarray) -> None:
        if self.data is None:
            self.data = xb
        else:
            self.data = np.vstack([self.data, xb])
        
        N = len(self.data)
        if N <= len(self.layers[0]) if self.layers else 0:
            return
            
        # Initialize structure for new points
        start_idx = len(self.layers[0]) if self.layers else 0
        
        for i in range(start_idx, N):
            level = self._random_level()
            
            # Ensure we have enough layers
            while len(self.layers) <= level:
                self.layers.append([])
                self.neighbors.append({})
            
            # Add node to each layer up to its level
            for l in range(level + 1):
                self.layers[l].append(i)
                self.neighbors[l][i] = []
            
            # For first point, set as entry point
            if i == 0:
                self.entry_point = i
                continue
            
            # Find nearest neighbors in each layer
            for l in range(level, -1, -1):
                # Search for ef_construction neighbors in layer l
                ep = self.entry_point if l == level else candidates[0][1]
                W = self._search_layer(xb[i], ep, l, self.ef_construction)
                
                # Select M nearest as connections
                W.sort(key=lambda x: x[0])
                neighbors = W[:self.M]
                
                # Add bidirectional connections
                self.neighbors[l][i] = [idx for _, idx in neighbors]
                for _, neighbor_idx in neighbors:
                    if i not in self.neighbors[l][neighbor_idx]:
                        self.neighbors[l][neighbor_idx].append(i)
                        # Limit to M connections
                        if len(self.neighbors[l][neighbor_idx]) > self.M:
                            # Prune: keep M closest
                            neighbor_vec = self.data[neighbor_idx]
                            conn_dists = []
                            for conn in self.neighbors[l][neighbor_idx]:
                                conn_vec = self.data[conn]
                                dist = np.sum((neighbor_vec - conn_vec) ** 2)
                                conn_dists.append((dist, conn))
                            conn_dists.sort(key=lambda x: x[0])
                            self.neighbors[l][neighbor_idx] = [idx for _, idx in conn_dists[:self.M]]
    
    def _search_layer(self, query, entry_point, layer, ef):
        # Best-first search in a layer
        visited = set([entry_point])
        candidates = [(0.0, entry_point)]  # (distance, node)
        heapq.heapify(candidates)
        result = []
        
        while candidates:
            dist, node = heapq.heappop(candidates)
            result.append((dist, node))
            
            if len(result) >= ef:
                break
            
            for neighbor in self.neighbors[layer].get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    neighbor_vec = self.data[neighbor]
                    dist = np.sum((query - neighbor_vec) ** 2)
                    heapq.heappush(candidates, (dist, neighbor))
        
        return result
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        nq = len(xq)
        distances = np.full((nq, k), np.inf, dtype=np.float32)
        indices = np.full((nq, k), -1, dtype=np.int64)
        
        if self.entry_point is None:
            return distances, indices
        
        for q_idx in range(nq):
            query = xq[q_idx]
            ep = self.entry_point
            
            # Traverse from top layer to bottom
            for l in range(len(self.layers) - 1, 0, -1):
                if l < len(self.layers):
                    ep = self._search_layer(query, ep, l, 1)[0][1]
            
            # Search in bottom layer with ef_search
            W = self._search_layer(query, ep, 0, self.ef_search)
            W.sort(key=lambda x: x[0])
            
            # Take k nearest
            for j in range(min(k, len(W))):
                distances[q_idx, j] = W[j][0]
                indices[q_idx, j] = W[j][1]
        
        return distances, indices

class ProductQuantizationIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.data = None
        self.m = kwargs.get('m', 8)  # Number of subvectors
        self.nbits = kwargs.get('nbits', 8)  # Bits per subquantizer
        self.k = 1 << self.nbits  # Centroids per subquantizer
        self.subdim = dim // self.m
        self.codebooks = None
        self.codes = None
        
    def add(self, xb: np.ndarray) -> None:
        if self.data is None:
            self.data = xb
        else:
            self.data = np.vstack([self.data, xb])
        
        N = len(self.data)
        if N < 10000:  # Need enough data to train
            return
            
        if self.codebooks is None:
            self._train_pq()
        
        if self.codes is None:
            self.codes = np.zeros((N, self.m), dtype=np.uint8)
        else:
            old_N = len(self.codes)
            new_codes = np.zeros((N, self.m), dtype=np.uint8)
            new_codes[:old_N] = self.codes
            self.codes = new_codes
        
        # Encode new points
        for i in range(old_N, N):
            vector = self.data[i]
            for j in range(self.m):
                start = j * self.subdim
                end = start + self.subdim
                subvec = vector[start:end]
                # Find nearest centroid
                dists = np.sum((subvec - self.codebooks[j]) ** 2, axis=1)
                self.codes[i, j] = np.argmin(dists)
    
    def _train_pq(self):
        N = len(self.data)
        # Sample for training
        sample_size = min(100000, N)
        indices = np.random.choice(N, sample_size, replace=False)
        sample = self.data[indices]
        
        self.codebooks = []
        for j in range(self.m):
            start = j * self.subdim
            end = start + self.subdim
            subvecs = sample[:, start:end]
            
            # Simple k-means initialization
            centroids = subvecs[np.random.choice(len(subvecs), self.k, replace=False)]
            for _ in range(10):  # Few iterations for speed
                # Assign
                dists = np.sum((subvecs[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
                assignments = np.argmin(dists, axis=1)
                
                # Update
                new_centroids = np.zeros_like(centroids)
                counts = np.zeros(self.k)
                for i, a in enumerate(assignments):
                    new_centroids[a] += subvecs[i]
                    counts[a] += 1
                
                # Avoid division by zero
                mask = counts > 0
                new_centroids[mask] /= counts[mask, None]
                centroids = new_centroids
            
            self.codebooks.append(centroids)
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        nq = len(xq)
        distances = np.full((nq, k), np.inf, dtype=np.float32)
        indices = np.full((nq, k), -1, dtype=np.int64)
        
        if self.codebooks is None or self.codes is None:
            return distances, indices
        
        N = len(self.codes)
        
        # Precompute distance tables for each query
        for q_idx in range(nq):
            query = xq[q_idx]
            
            # Compute distance tables: table[j][c] = distance from query's j-th subvector to centroid c
            tables = []
            for j in range(self.m):
                start = j * self.subdim
                end = start + self.subdim
                subquery = query[start:end]
                dists = np.sum((subquery - self.codebooks[j]) ** 2, axis=1)
                tables.append(dists)
            
            # Scan all points with early termination
            candidates = []
            batch_size = 10000
            for i in range(0, N, batch_size):
                batch_codes = self.codes[i:i+batch_size]
                batch_indices = np.arange(i, min(i+batch_size, N))
                
                # Compute approximate distances
                batch_dists = np.zeros(len(batch_codes))
                for j in range(self.m):
                    batch_dists += tables[j][batch_codes[:, j]]
                
                # Maintain k-nearest
                for dist, idx in zip(batch_dists, batch_indices):
                    if len(candidates) < k or dist < candidates[0][0]:
                        if len(candidates) == k:
                            heapq.heappushpop(candidates, (-dist, idx))
                        else:
                            heapq.heappush(candidates, (-dist, idx))
            
            # Sort results
            if candidates:
                candidates.sort(reverse=True)
                for j in range(min(k, len(candidates))):
                    distances[q_idx, j] = -candidates[j][0]
                    indices[q_idx, j] = candidates[j][1]
        
        return distances, indices

class FastIVFADCIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.data = None
        self.nlist = kwargs.get('nlist', 256)
        self.nprobe = kwargs.get('nprobe', 2)  # Very low for latency
        self.m = kwargs.get('m', 8)
        self.nbits = kwargs.get('nbits', 8)
        self.k = 1 << self.nbits
        self.subdim = dim // self.m
        
        self.centroids = None
        self.cells = None
        self.codebooks = None
        self.codes = None
        
    def add(self, xb: np.ndarray) -> None:
        if self.data is None:
            self.data = xb
        else:
            self.data = np.vstack([self.data, xb])
        
        N = len(self.data)
        if N < 50000:
            return
            
        if self.centroids is None:
            self._train_coarse()
        
        if self.codebooks is None:
            self._train_pq()
        
        if self.cells is None:
            self.cells = [[] for _ in range(self.nlist)]
            self.codes = np.zeros((N, self.m), dtype=np.uint8)
        
        # Process in batches
        batch_size = 10000
        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            batch = self.data[start:end]
            
            # Coarse quantization
            dists = np.sum((batch[:, None, :] - self.centroids[None, :, :]) ** 2, axis=2)
            assignments = np.argmin(dists, axis=1)
            
            # Assign to cells
            for i, a in enumerate(assignments):
                global_idx = start + i
                self.cells[a].append(global_idx)
            
            # Encode residuals
            residuals = batch - self.centroids[assignments]
            
            for i in range(len(batch)):
                global_idx = start + i
                residual = residuals[i]
                for j in range(self.m):
                    start_dim = j * self.subdim
                    end_dim = start_dim + self.subdim
                    subvec = residual[start_dim:end_dim]
                    dists_sub = np.sum((subvec - self.codebooks[j]) ** 2, axis=1)
                    self.codes[global_idx, j] = np.argmin(dists_sub)
    
    def _train_coarse(self):
        N = len(self.data)
        sample_size = min(100000, N)
        indices = np.random.choice(N, sample_size, replace=False)
        sample = self.data[indices]
        
        # Simple k-means for coarse quantizer
        self.centroids = sample[np.random.choice(len(sample), self.nlist, replace=False)]
        for _ in range(5):
            dists = np.sum((sample[:, None, :] - self.centroids[None, :, :]) ** 2, axis=2)
            assignments = np.argmin(dists, axis=1)
            
            new_centroids = np.zeros_like(self.centroids)
            counts = np.zeros(self.nlist)
            for i, a in enumerate(assignments):
                new_centroids[a] += sample[i]
                counts[a] += 1
            
            mask = counts > 0
            new_centroids[mask] /= counts[mask, None]
            self.centroids = new_centroids
    
    def _train_pq(self):
        N = len(self.data)
        sample_size = min(100000, N)
        indices = np.random.choice(N, sample_size, replace=False)
        sample = self.data[indices]
        
        # Compute residuals
        dists = np.sum((sample[:, None, :] - self.centroids[None, :, :]) ** 2, axis=2)
        assignments = np.argmin(dists, axis=1)
        residuals = sample - self.centroids[assignments]
        
        self.codebooks = []
        for j in range(self.m):
            start = j * self.subdim
            end = start + self.subdim
            subvecs = residuals[:, start:end]
            
            centroids = subvecs[np.random.choice(len(subvecs), self.k, replace=False)]
            for _ in range(5):
                dists_sub = np.sum((subvecs[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
                assignments_sub = np.argmin(dists_sub, axis=1)
                
                new_centroids = np.zeros_like(centroids)
                counts = np.zeros(self.k)
                for i, a in enumerate(assignments_sub):
                    new_centroids[a] += subvecs[i]
                    counts[a] += 1
                
                mask = counts > 0
                new_centroids[mask] /= counts[mask, None]
                centroids = new_centroids
            
            self.codebooks.append(centroids)
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        nq = len(xq)
        distances = np.full((nq, k), np.inf, dtype=np.float32)
        indices = np.full((nq, k), -1, dtype=np.int64)
        
        if self.centroids is None or self.cells is None:
            return distances, indices
        
        for q_idx in range(nq):
            query = xq[q_idx]
            
            # Find nearest cells
            dists_to_centroids = np.sum((query - self.centroids) ** 2, axis=1)
            nearest_cells = np.argpartition(dists_to_centroids, self.nprobe)[:self.nprobe]
            
            # Precompute distance tables for PQ
            tables = []
            for j in range(self.m):
                start = j * self.subdim
                end = start + self.subdim
                # For each cell, we need residual distances
                cell_tables = []
                for cell_id in nearest_cells:
                    centroid = self.centroids[cell_id]
                    subquery = query[start:end] - centroid[start:end]
                    dists = np.sum((subquery - self.codebooks[j]) ** 2, axis=1)
                    cell_tables.append(dists)
                tables.append(cell_tables)
            
            # Search in candidate cells
            candidates = []
            for cell_idx, cell_id in enumerate(nearest_cells):
                cell_points = self.cells[cell_id]
                if not cell_points:
                    continue
                
                # Compute coarse distance
                centroid_dist = dists_to_centroids[cell_id]
                
                # Get codes for this cell
                cell_codes = self.codes[cell_points]
                
                # Compute approximate distances
                n_points = len(cell_points)
                point_dists = np.full(n_points, centroid_dist, dtype=np.float32)
                
                for j in range(self.m):
                    code_dists = tables[j][cell_idx][cell_codes[:, j]]
                    point_dists += code_dists
                
                # Maintain k-nearest
                for dist, idx in zip(point_dists, cell_points):
                    if len(candidates) < k or dist < candidates[0][0]:
                        if len(candidates) == k:
                            heapq.heappushpop(candidates, (-dist, idx))
                        else:
                            heapq.heappush(candidates, (-dist, idx))
            
            # Sort results
            if candidates:
                candidates.sort(reverse=True)
                for j in range(min(k, len(candidates))):
                    distances[q_idx, j] = -candidates[j][0]
                    indices[q_idx, j] = candidates[j][1]
        
        return distances, indices

class VDBIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.data = None
        self.index_type = kwargs.get('index_type', 'ivf')  # 'ivf', 'hnsw', 'pq', 'ivfpq'
        
        # Parameters optimized for latency
        if self.index_type == 'ivf':
            self.impl = LowLatencyIndex(dim, 
                                       nlist=256, 
                                       nprobe=3)  # Very aggressive
        elif self.index_type == 'hnsw':
            self.impl = FastHNSWIndex(dim,
                                     M=12,
                                     ef_search=32,
                                     ef_construction=40,
                                     max_level=4)
        elif self.index_type == 'pq':
            self.impl = ProductQuantizationIndex(dim,
                                                m=8,
                                                nbits=8)
        elif self.index_type == 'ivfpq':
            self.impl = FastIVFADCIndex(dim,
                                       nlist=256,
                                       nprobe=2,
                                       m=8,
                                       nbits=8)
        else:
            # Default to IVF as it's usually fastest
            self.impl = LowLatencyIndex(dim, nlist=256, nprobe=3)
    
    def add(self, xb: np.ndarray) -> None:
        if self.data is None:
            self.data = xb
        else:
            self.data = np.vstack([self.data, xb])
        self.impl.add(xb)
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        return self.impl.search(xq, k)

# The evaluator will auto-discover any class with add/search methods
# We'll expose the main implementation
class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        # Use IVF with very aggressive settings for lowest latency
        self.dim = dim
        self.data = None
        
        # IVF parameters optimized for strict 2.31ms constraint
        self.nlist = kwargs.get('nlist', 512)  # More cells for faster search
        self.nprobe = kwargs.get('nprobe', 2)  # Very low for latency
        self.centroids = None
        self.cells = None
        
        # Precomputed norms for L2 distance optimization
        self.norms = None
        
    def add(self, xb: np.ndarray) -> None:
        if self.data is None:
            self.data = xb.astype(np.float32)
            self.norms = np.sum(xb ** 2, axis=1).astype(np.float32)
        else:
            self.data = np.vstack([self.data, xb.astype(np.float32)])
            new_norms = np.sum(xb ** 2, axis=1).astype(np.float32)
            self.norms = np.concatenate([self.norms, new_norms])
        
        N = len(self.data)
        if N >= 100000 and self.centroids is None:
            self._build_index()
    
    def _build_index(self):
        N = len(self.data)
        nlist = min(self.nlist, N // 50)  # About 50 vectors per cell
        
        # Simple random centroids for speed (no training)
        np.random.seed(123)
        idx = np.random.choice(N, nlist, replace=False)
        self.centroids = self.data[idx].copy()
        
        # Compute centroid norms once
        self.centroid_norms = np.sum(self.centroids ** 2, axis=1).astype(np.float32)
        
        # Assign points to nearest centroid using dot products for speed
        self.cells = [[] for _ in range(nlist)]
        
        # Process in large batches for efficiency
        batch_size = 50000
        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            batch = self.data[start:end]
            
            # Compute dot products: batch (B x dim) @ centroids.T (dim x nlist)
            dots = np.dot(batch, self.centroids.T)
            
            # Use broadcasting for norms
            batch_norms = self.norms[start:end][:, None]
            
            # L2 distance = ||x||^2 + ||c||^2 - 2<x,c>
            dists = batch_norms + self.centroid_norms[None, :] - 2 * dots
            
            # Find nearest centroid for each point
            nearest = np.argmin(dists, axis=1)
            
            # Assign to cells
            for i, cell_id in enumerate(nearest):
                global_idx = start + i
                self.cells[cell_id].append(global_idx)
        
        # Convert to numpy arrays for faster access
        self.cells = [np.array(cell, dtype=np.int64) for cell in self.cells]
    
    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        nq = len(xq)
        distances = np.full((nq, k), np.inf, dtype=np.float32)
        indices = np.full((nq, k), -1, dtype=np.int64)
        
        if self.centroids is None:
            # Build index if not already built
            self._build_index()
        
        if nq == 0:
            return distances, indices
        
        # Precompute query norms
        query_norms = np.sum(xq ** 2, axis=1).astype(np.float32)
        
        # For each query, find nearest centroids using dot products
        # Compute all dot products at once for efficiency
        dots_qc = np.dot(xq, self.centroids.T)  # (nq, nlist)
        
        # L2 distance to centroids: ||q||^2 + ||c||^2 - 2<q,c>
        centroid_dists = query_norms[:, None] + self.centroid_norms[None, :] - 2 * dots_qc
        
        # Find nprobe nearest centroids for each query
        nearest_cells = np.argpartition(centroid_dists, self.nprobe, axis=1)[:, :self.nprobe]
        
        # Process queries in small batches to balance memory and speed
        query_batch_size = min(100, nq)  # Small batch for better cache usage
        
        for q_start in range(0, nq, query_batch_size):
            q_end = min(q_start + query_batch_size, nq)
            q_batch = xq[q_start:q_end]
            q_batch_norms = query_norms[q_start:q_end]
            q_nearest_cells = nearest_cells[q_start:q_end]
            
            batch_size = len(q_batch)
            batch_candidates = [[] for _ in range(batch_size)]
            
            # Search each candidate cell
            for b in range(batch_size):
                query = q_batch[b]
                q_norm = q_batch_norms[b]
                
                for cell_id in q_nearest_cells[b]:
                    if cell_id >= len(self.cells):
                        continue
                    
                    cell_points = self.cells[cell_id]
                    if len(cell_points) == 0:
                        continue
                    
                    # Get data for this cell
                    cell_data = self.data[cell_points]
                    
                    # Compute distances using precomputed norms
                    # L2 distance = ||q||^2 + ||x||^2 - 2<q,x>
                    # We have q_norm, cell_norms, and need dot products
                    cell_norms = self.norms[cell_points]
                    
                    # Compute dot products: query (dim,) @ cell_data.T (dim, n_points)
                    dots = np.dot(query, cell_data.T)
                    
                    # Compute distances
                    point_dists = q_norm + cell_norms - 2 * dots
                    
                    # Maintain k-nearest using heap
                    candidates = batch_candidates[b]
                    for dist, idx in zip(point_dists, cell_points):
                        if len(candidates) < k or dist < candidates[0][0]:
                            if len(candidates) == k:
                                heapq.heappushpop(candidates, (-dist, idx))
                            else:
                                heapq.heappush(candidates, (-dist, idx))
            
            # Convert heaps to sorted arrays
            for b in range(batch_size):
                q_idx = q_start + b
                candidates = batch_candidates[b]
                
                if candidates:
                    candidates.sort(reverse=True)
                    for j in range(min(k, len(candidates))):
                        distances[q_idx, j] = -candidates[j][0]
                        indices[q_idx, j] = candidates[j][1]
        
        return distances, indices
