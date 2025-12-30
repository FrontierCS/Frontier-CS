import json
import os
import networkx as nx
import heapq
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import math

class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts}

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        self.num_partitions = num_partitions

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Design routing paths for broadcasting data partitions to multiple destinations.
    
    Strategy: Multi-commodity flow approximation using shortest paths with capacity awareness.
    For each partition, we try to distribute load across different paths to avoid bottlenecks.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Initialize edge usage counters
    edge_usage = defaultdict(int)  # Count of partitions using each edge
    
    # Get provider from node string
    def get_provider(node: str) -> str:
        return node.split(':')[0]
    
    # Default bandwidth limits (Gbps) per VM (will be multiplied by num_vms later)
    # These are per-region limits, we'll use them for guidance
    provider_limits = {
        'aws': {'ingress': 10, 'egress': 5},
        'gcp': {'ingress': 16, 'egress': 7},
        'azure': {'ingress': 16, 'egress': 16}
    }
    
    # Precompute k-shortest paths for each destination
    K = min(3, num_partitions)  # Use up to 3 different paths per destination
    
    # For each destination, find K shortest paths by cost
    dst_paths = {}
    for dst in dsts:
        try:
            # Get all simple paths, sorted by total cost
            paths = []
            for path in nx.all_simple_paths(G, src, dst):
                total_cost = sum(G[u][v]['cost'] for u, v in zip(path[:-1], path[1:]))
                paths.append((total_cost, path))
            paths.sort(key=lambda x: x[0])
            dst_paths[dst] = [p[1] for p in paths[:K]]
        except:
            # Fallback to single shortest path
            try:
                path = nx.shortest_path(G, src, dst, weight='cost')
                dst_paths[dst] = [path]
            except:
                dst_paths[dst] = []
    
    # Assign partitions to paths in round-robin fashion to distribute load
    for dst in dsts:
        if not dst_paths[dst]:
            continue
            
        # Get available paths for this destination
        available_paths = dst_paths[dst]
        
        # Assign each partition to a path (round-robin)
        for partition in range(num_partitions):
            path_idx = partition % len(available_paths)
            path = available_paths[path_idx]
            
            # Record the path
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = G[u][v]
                bc_topology.append_dst_partition_path(dst, partition, [u, v, edge_data])
                edge_usage[(u, v)] += 1
    
    # Post-processing: Try to optimize paths that share bottleneck edges
    # Identify bottleneck edges (high usage relative to throughput)
    bottleneck_edges = []
    for (u, v), usage in edge_usage.items():
        if usage > 0 and 'throughput' in G[u][v]:
            throughput = G[u][v]['throughput']
            if usage > throughput * 0.5:  # Arbitrary threshold
                bottleneck_edges.append((u, v))
    
    # For bottleneck edges, try to reroute some partitions
    for (bu, bv) in bottleneck_edges:
        # Find affected destinations and partitions
        for dst in dsts:
            for partition in range(num_partitions):
                partition_str = str(partition)
                if (bc_topology.paths[dst][partition_str] is not None and 
                    any(e[0] == bu and e[1] == bv for e in bc_topology.paths[dst][partition_str])):
                    
                    # Try to find alternative path avoiding this edge
                    try:
                        # Create temporary graph without bottleneck edge
                        G_temp = G.copy()
                        if G_temp.has_edge(bu, bv):
                            G_temp.remove_edge(bu, bv)
                        
                        # Find alternative path
                        alt_path = nx.shortest_path(G_temp, src, dst, weight='cost')
                        
                        # Check if alternative is reasonable
                        alt_cost = sum(G_temp[u][v]['cost'] for u, v in zip(alt_path[:-1], alt_path[1:]))
                        orig_cost = sum(G[e[0]][e[1]]['cost'] for e in bc_topology.paths[dst][partition_str])
                        
                        # Switch if alternative is not too expensive (within 20%)
                        if alt_cost <= orig_cost * 1.2:
                            # Update edge usage
                            for e in bc_topology.paths[dst][partition_str]:
                                edge_usage[(e[0], e[1])] -= 1
                            
                            # Set new path
                            new_edges = []
                            for i in range(len(alt_path) - 1):
                                u, v = alt_path[i], alt_path[i + 1]
                                edge_data = G[u][v]
                                new_edges.append([u, v, edge_data])
                                edge_usage[(u, v)] += 1
                            
                            bc_topology.set_dst_partition_paths(dst, partition, new_edges)
                    except:
                        pass  # Keep original path if no alternative
    
    return bc_topology

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Read specification file
        with open(spec_path, 'r') as f:
            spec = json.load(f)
        
        config_files = spec.get("config_files", [])
        num_vms = spec.get("num_vms", 2)
        
        # Generate the algorithm code as a string
        code = '''import json
import os
import networkx as nx
import heapq
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import math

class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts}

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        self.num_partitions = num_partitions

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Enhanced search algorithm with better load balancing.
    Uses multiple metrics to select paths and dynamically avoids bottlenecks.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Get provider from node string
    def get_provider(node: str) -> str:
        return node.split(':')[0]
    
    # Track edge usage for load balancing
    edge_usage = defaultdict(int)
    
    # For each destination, precompute candidate paths
    # We'll use a combination of cost and capacity
    for dst in dsts:
        # Find multiple paths using a modified Dijkstra that considers both cost and capacity
        paths_by_partition = find_paths_for_destination(src, dst, G, num_partitions, edge_usage)
        
        # Assign paths to partitions
        for partition in range(num_partitions):
            if partition < len(paths_by_partition):
                path = paths_by_partition[partition]
                # Record the path
                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    edge_data = G[u][v]
                    bc_topology.append_dst_partition_path(dst, partition, [u, v, edge_data])
                    edge_usage[(u, v)] += 1
    
    return bc_topology

def find_paths_for_destination(src: str, dst: str, G: nx.DiGraph, num_partitions: int, 
                               edge_usage: Dict[Tuple[str, str], int]) -> List[List[str]]:
    """Find multiple diverse paths for a destination."""
    paths = []
    
    # First path: shortest by cost
    try:
        path1 = nx.shortest_path(G, src, dst, weight='cost')
        paths.append(path1)
    except:
        pass
    
    # Second path: try to find path with good throughput
    if len(paths) < num_partitions:
        try:
            # Modify edge weights to favor higher throughput
            G_temp = G.copy()
            for u, v in G_temp.edges():
                # Inverse of throughput as weight (higher throughput = lower weight)
                if 'throughput' in G_temp[u][v]:
                    throughput = max(G_temp[u][v]['throughput'], 0.1)  # Avoid division by zero
                    # Combine cost and throughput
                    G_temp[u][v]['combined_weight'] = G_temp[u][v]['cost'] * 0.7 + (1.0 / throughput) * 0.3
                else:
                    G_temp[u][v]['combined_weight'] = G_temp[u][v]['cost']
            
            path2 = nx.shortest_path(G_temp, src, dst, weight='combined_weight')
            if path2 not in paths:
                paths.append(path2)
        except:
            pass
    
    # Third path: try to avoid edges with high current usage
    if len(paths) < num_partitions:
        try:
            G_temp = G.copy()
            for u, v in G_temp.edges():
                current_usage = edge_usage.get((u, v), 0)
                # Penalize edges that are already heavily used
                usage_penalty = current_usage * 0.1
                G_temp[u][v]['usage_weight'] = G_temp[u][v]['cost'] + usage_penalty
            
            path3 = nx.shortest_path(G_temp, src, dst, weight='usage_weight')
            if path3 not in paths:
                paths.append(path3)
        except:
            pass
    
    # If we still need more paths, use k-shortest paths
    if len(paths) < num_partitions:
        try:
            # Use Yen's algorithm for k-shortest paths
            k = num_partitions - len(paths)
            gen = nx.shortest_simple_paths(G, src, dst, weight='cost')
            for i, path in enumerate(gen):
                if path not in paths:
                    paths.append(path)
                if i >= k - 1:
                    break
        except:
            pass
    
    # If we don't have enough unique paths, duplicate existing ones in round-robin
    if len(paths) < num_partitions:
        result = []
        for i in range(num_partitions):
            result.append(paths[i % len(paths)])
        return result
    
    return paths[:num_partitions]
'''
        
        return {"code": code}