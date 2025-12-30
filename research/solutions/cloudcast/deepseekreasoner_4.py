import networkx as nx
import random
import json
import math
import heapq
import itertools
from collections import defaultdict, deque
from typing import List, Dict, Set, Tuple, Optional
import copy

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int):
    """
    Design routing paths for broadcasting data partitions to multiple destinations.
    Uses a hybrid approach combining Steiner tree approximation with multi-path load balancing.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Configuration constants
    NUM_VMS = 2
    INSTANCE_RATE = 0.54  # $/hour
    
    # Provider identification helper
    def get_provider(node: str) -> str:
        return node.split(':')[0]
    
    # Get all nodes in the graph
    all_nodes = list(G.nodes())
    
    # Precompute shortest paths from source to all nodes
    shortest_paths = {}
    for node in all_nodes:
        try:
            shortest_paths[node] = nx.shortest_path(G, src, node, weight='cost')
        except nx.NetworkXNoPath:
            shortest_paths[node] = []
    
    # Build a Steiner tree approximation for all destinations
    # Start with shortest paths to all destinations
    steiner_edges = set()
    steiner_nodes = set([src])
    
    for dst in dsts:
        if dst in shortest_paths and shortest_paths[dst]:
            path = shortest_paths[dst]
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                steiner_edges.add((u, v))
                steiner_nodes.add(u)
                steiner_nodes.add(v)
    
    # Create a subgraph of the Steiner tree
    steiner_graph = nx.DiGraph()
    for u, v in steiner_edges:
        if G.has_edge(u, v):
            steiner_graph.add_edge(u, v, **G[u][v])
    
    # Assign partitions to different paths for load balancing
    # Use BFS from source to get multiple paths to each destination
    
    def find_k_paths(src_node, dst_node, k=3):
        """Find k simple paths from src to dst using cost as primary metric"""
        paths = []
        try:
            # Get shortest path first
            shortest = nx.shortest_path(G, src_node, dst_node, weight='cost')
            if shortest:
                paths.append(shortest)
            
            # Try to find alternative paths using Yen's algorithm if available
            # (simplified version for efficiency)
            if len(paths) < k:
                # Try removing edges from the shortest path and find alternatives
                for i in range(len(shortest) - 1):
                    u, v = shortest[i], shortest[i + 1]
                    if G.has_edge(u, v):
                        # Temporarily remove this edge
                        edge_data = G[u][v]
                        G.remove_edge(u, v)
                        
                        try:
                            alt_path = nx.shortest_path(G, src_node, dst_node, weight='cost')
                            if alt_path and alt_path not in paths:
                                paths.append(alt_path)
                        except nx.NetworkXNoPath:
                            pass
                        
                        # Restore the edge
                        G.add_edge(u, v, **edge_data)
                        
                        if len(paths) >= k:
                            break
            
            # If still not enough paths, use random walk to generate more
            if len(paths) < k:
                for _ in range(3 * (k - len(paths))):
                    path = [src_node]
                    current = src_node
                    visited = set([src_node])
                    
                    while current != dst_node and len(path) < 10:
                        # Get outgoing edges
                        neighbors = list(G.successors(current))
                        if not neighbors:
                            break
                        
                        # Prefer neighbors that lead toward destination
                        # Use cost + heuristic (shortest path length)
                        best_neighbor = None
                        best_score = float('inf')
                        
                        for neighbor in neighbors:
                            if neighbor in visited:
                                continue
                            
                            # Calculate score: cost + distance to destination
                            edge_cost = G[current][neighbor]['cost']
                            try:
                                dist_to_dst = len(nx.shortest_path(G, neighbor, dst_node))
                            except:
                                dist_to_dst = 10  # Large penalty
                            
                            score = edge_cost + 0.1 * dist_to_dst
                            
                            if score < best_score:
                                best_score = score
                                best_neighbor = neighbor
                        
                        if best_neighbor is None:
                            # No unvisited neighbors, backtrack
                            if len(path) > 1:
                                path.pop()
                                current = path[-1]
                                visited.remove(path[-1])
                                continue
                            else:
                                break
                        
                        path.append(best_neighbor)
                        visited.add(best_neighbor)
                        current = best_neighbor
                    
                    if current == dst_node and path not in paths:
                        paths.append(path)
                    
                    if len(paths) >= k:
                        break
            
            return paths[:k]
            
        except Exception as e:
            # Fallback to single shortest path
            try:
                path = nx.shortest_path(G, src_node, dst_node, weight='cost')
                return [path] if path else []
            except:
                return []
    
    # Assign partitions to paths
    # For each destination, assign partitions to different paths in round-robin
    for dst_idx, dst in enumerate(dsts):
        # Find multiple paths to this destination
        k_paths = find_k_paths(src, dst, min(3, num_partitions))
        
        if not k_paths:
            # Fallback: use shortest path for all partitions
            try:
                path = nx.shortest_path(G, src, dst, weight='cost')
                if path:
                    for partition_id in range(num_partitions):
                        edges = []
                        for i in range(len(path) - 1):
                            u, v = path[i], path[i + 1]
                            edges.append([u, v, G[u][v]])
                        bc_topology.set_dst_partition_paths(dst, partition_id, edges)
            except:
                # Last resort: use any simple path
                try:
                    for path in nx.all_simple_paths(G, src, dst, cutoff=10):
                        if path:
                            for partition_id in range(num_partitions):
                                edges = []
                                for i in range(len(path) - 1):
                                    u, v = path[i], path[i + 1]
                                    edges.append([u, v, G[u][v]])
                                bc_topology.set_dst_partition_paths(dst, partition_id, edges)
                            break
                except:
                    pass
        else:
            # Distribute partitions among available paths
            for partition_id in range(num_partitions):
                path_idx = partition_id % len(k_paths)
                path = k_paths[path_idx]
                edges = []
                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    edges.append([u, v, G[u][v]])
                bc_topology.set_dst_partition_paths(dst, partition_id, edges)
    
    # Optional: Try to improve the solution by balancing load
    # This is a simple heuristic that might help
    
    return bc_topology

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Read the specification
        if spec_path:
            try:
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                
                # Extract configuration
                config_files = spec.get('config_files', [])
                num_vms = spec.get('num_vms', 2)
                
                # Load the first config file to understand the structure
                if config_files:
                    with open(config_files[0], 'r') as f:
                        config = json.load(f)
            except:
                pass
        
        # Return the algorithm code
        code = '''
import networkx as nx
import random
import json
import math
import heapq
import itertools
from collections import defaultdict, deque
from typing import List, Dict, Set, Tuple, Optional
import copy

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int):
    """
    Design routing paths for broadcasting data partitions to multiple destinations.
    Uses a hybrid approach combining Steiner tree approximation with multi-path load balancing.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Configuration constants
    NUM_VMS = 2
    INSTANCE_RATE = 0.54  # $/hour
    
    # Provider identification helper
    def get_provider(node: str) -> str:
        return node.split(':')[0]
    
    # Get all nodes in the graph
    all_nodes = list(G.nodes())
    
    # Precompute shortest paths from source to all nodes
    shortest_paths = {}
    for node in all_nodes:
        try:
            shortest_paths[node] = nx.shortest_path(G, src, node, weight='cost')
        except nx.NetworkXNoPath:
            shortest_paths[node] = []
    
    # Build a Steiner tree approximation for all destinations
    # Start with shortest paths to all destinations
    steiner_edges = set()
    steiner_nodes = set([src])
    
    for dst in dsts:
        if dst in shortest_paths and shortest_paths[dst]:
            path = shortest_paths[dst]
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                steiner_edges.add((u, v))
                steiner_nodes.add(u)
                steiner_nodes.add(v)
    
    # Create a subgraph of the Steiner tree
    steiner_graph = nx.DiGraph()
    for u, v in steiner_edges:
        if G.has_edge(u, v):
            steiner_graph.add_edge(u, v, **G[u][v])
    
    # Assign partitions to different paths for load balancing
    # Use BFS from source to get multiple paths to each destination
    
    def find_k_paths(src_node, dst_node, k=3):
        """Find k simple paths from src to dst using cost as primary metric"""
        paths = []
        try:
            # Get shortest path first
            shortest = nx.shortest_path(G, src_node, dst_node, weight='cost')
            if shortest:
                paths.append(shortest)
            
            # Try to find alternative paths using Yen's algorithm if available
            # (simplified version for efficiency)
            if len(paths) < k:
                # Try removing edges from the shortest path and find alternatives
                for i in range(len(shortest) - 1):
                    u, v = shortest[i], shortest[i + 1]
                    if G.has_edge(u, v):
                        # Temporarily remove this edge
                        edge_data = G[u][v]
                        G.remove_edge(u, v)
                        
                        try:
                            alt_path = nx.shortest_path(G, src_node, dst_node, weight='cost')
                            if alt_path and alt_path not in paths:
                                paths.append(alt_path)
                        except nx.NetworkXNoPath:
                            pass
                        
                        # Restore the edge
                        G.add_edge(u, v, **edge_data)
                        
                        if len(paths) >= k:
                            break
            
            # If still not enough paths, use random walk to generate more
            if len(paths) < k:
                for _ in range(3 * (k - len(paths))):
                    path = [src_node]
                    current = src_node
                    visited = set([src_node])
                    
                    while current != dst_node and len(path) < 10:
                        # Get outgoing edges
                        neighbors = list(G.successors(current))
                        if not neighbors:
                            break
                        
                        # Prefer neighbors that lead toward destination
                        # Use cost + heuristic (shortest path length)
                        best_neighbor = None
                        best_score = float('inf')
                        
                        for neighbor in neighbors:
                            if neighbor in visited:
                                continue
                            
                            # Calculate score: cost + distance to destination
                            edge_cost = G[current][neighbor]['cost']
                            try:
                                dist_to_dst = len(nx.shortest_path(G, neighbor, dst_node))
                            except:
                                dist_to_dst = 10  # Large penalty
                            
                            score = edge_cost + 0.1 * dist_to_dst
                            
                            if score < best_score:
                                best_score = score
                                best_neighbor = neighbor
                        
                        if best_neighbor is None:
                            # No unvisited neighbors, backtrack
                            if len(path) > 1:
                                path.pop()
                                current = path[-1]
                                visited.remove(path[-1])
                                continue
                            else:
                                break
                        
                        path.append(best_neighbor)
                        visited.add(best_neighbor)
                        current = best_neighbor
                    
                    if current == dst_node and path not in paths:
                        paths.append(path)
                    
                    if len(paths) >= k:
                        break
            
            return paths[:k]
            
        except Exception as e:
            # Fallback to single shortest path
            try:
                path = nx.shortest_path(G, src_node, dst_node, weight='cost')
                return [path] if path else []
            except:
                return []
    
    # Assign partitions to paths
    # For each destination, assign partitions to different paths in round-robin
    for dst_idx, dst in enumerate(dsts):
        # Find multiple paths to this destination
        k_paths = find_k_paths(src, dst, min(3, num_partitions))
        
        if not k_paths:
            # Fallback: use shortest path for all partitions
            try:
                path = nx.shortest_path(G, src, dst, weight='cost')
                if path:
                    for partition_id in range(num_partitions):
                        edges = []
                        for i in range(len(path) - 1):
                            u, v = path[i], path[i + 1]
                            edges.append([u, v, G[u][v]])
                        bc_topology.set_dst_partition_paths(dst, partition_id, edges)
            except:
                # Last resort: use any simple path
                try:
                    for path in nx.all_simple_paths(G, src, dst, cutoff=10):
                        if path:
                            for partition_id in range(num_partitions):
                                edges = []
                                for i in range(len(path) - 1):
                                    u, v = path[i], path[i + 1]
                                    edges.append([u, v, G[u][v]])
                                bc_topology.set_dst_partition_paths(dst, partition_id, edges)
                            break
                except:
                    pass
        else:
            # Distribute partitions among available paths
            for partition_id in range(num_partitions):
                path_idx = partition_id % len(k_paths)
                path = k_paths[path_idx]
                edges = []
                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    edges.append([u, v, G[u][v]])
                bc_topology.set_dst_partition_paths(dst, partition_id, edges)
    
    # Optional: Try to improve the solution by balancing load
    # This is a simple heuristic that might help
    
    return bc_topology
'''
        
        return {"code": code}