import json
import networkx as nx
import heapq
import math
from typing import Dict, List, Tuple, Set
import random

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int):
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Create a copy of graph with modified weights
    H = G.copy()
    
    # Precompute shortest path trees for each destination
    dst_paths = {}
    for dst in dsts:
        try:
            path = nx.shortest_path(H, src, dst, weight='cost')
            dst_paths[dst] = path
        except:
            # If no path exists, use direct path if edge exists
            if G.has_edge(src, dst):
                dst_paths[dst] = [src, dst]
    
    # Distribute partitions across different paths
    for dst in dsts:
        if dst not in dst_paths:
            continue
            
        base_path = dst_paths[dst]
        
        # Try to find alternative paths for load balancing
        alt_paths = [base_path]
        
        # Find k-shortest paths (k=3)
        try:
            k_paths = list(nx.shortest_simple_paths(H, src, dst, weight='cost'))
            for path in k_paths:
                if path not in alt_paths:
                    alt_paths.append(path)
                if len(alt_paths) >= 3:
                    break
        except:
            pass
        
        # Assign partitions to different paths in round-robin fashion
        for partition_id in range(num_partitions):
            path_idx = partition_id % len(alt_paths)
            path = alt_paths[path_idx]
            
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = H[u][v]
                bc_topology.append_dst_partition_path(dst, partition_id, 
                                                     [u, v, edge_data])
    
    return bc_topology

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        algorithm_code = '''
import json
import networkx as nx
import heapq
import math
from typing import Dict, List, Tuple, Set
import random
import copy

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int):
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Read bandwidth constraints from environment
    # These would be provided in practice but we need to estimate
    provider_limits = {
        'aws': {'ingress': 10, 'egress': 5},
        'gcp': {'ingress': 16, 'egress': 7},
        'azure': {'ingress': 16, 'egress': 16}
    }
    num_vms = 2
    
    # Helper to get provider from node
    def get_provider(node):
        if node.startswith('aws:'):
            return 'aws'
        elif node.startswith('gcp:'):
            return 'gcp'
        elif node.startswith('azure:'):
            return 'azure'
        return 'aws'  # default
    
    # Phase 1: Build initial Steiner tree approximation
    H = G.copy()
    
    # Create a virtual source that connects to all destinations
    # for Steiner tree computation
    virtual_src = '__virtual_source__'
    H.add_node(virtual_src)
    for dst in dsts:
        H.add_edge(virtual_src, dst, cost=0, throughput=float('inf'))
    
    # Use minimum spanning tree on metric closure
    metric_closure = {}
    for u in [src] + dsts:
        for v in [src] + dsts:
            if u != v:
                try:
                    dist = nx.shortest_path_length(H, u, v, weight='cost')
                    metric_closure[(u, v)] = dist
                except:
                    metric_closure[(u, v)] = float('inf')
    
    # Build MST on the set {src} ∪ dsts
    mst_edges = []
    nodes = [src] + dsts
    if len(nodes) > 1:
        # Prim's algorithm
        visited = {nodes[0]}
        while len(visited) < len(nodes):
            min_edge = None
            min_cost = float('inf')
            for u in visited:
                for v in nodes:
                    if v not in visited:
                        cost = metric_closure.get((u, v), float('inf'))
                        if cost < min_cost:
                            min_cost = cost
                            min_edge = (u, v, cost)
            if min_edge:
                u, v, _ = min_edge
                visited.add(v)
                mst_edges.append((u, v))
    
    # Convert MST edges to actual paths
    tree_paths = {}
    for u, v in mst_edges:
        try:
            path = nx.shortest_path(H, u, v, weight='cost')
            tree_paths[(u, v)] = path
        except:
            pass
    
    # Build the broadcast tree from source
    tree = nx.DiGraph()
    tree.add_node(src)
    
    # BFS from source through the MST
    queue = [src]
    while queue:
        u = queue.pop(0)
        for (u2, v), path in tree_paths.items():
            if u2 == u and v not in tree.nodes():
                # Add the path to tree
                for i in range(len(path) - 1):
                    a, b = path[i], path[i + 1]
                    if not tree.has_edge(a, b):
                        tree.add_edge(a, b, **H[a][b])
                queue.append(v)
    
    # Phase 2: Assign partitions with load balancing
    # First, compute all simple paths from src to each dst
    all_paths = {}
    for dst in dsts:
        paths = []
        try:
            # Get k-shortest paths
            for path in nx.shortest_simple_paths(G, src, dst, weight='cost'):
                paths.append(path)
                if len(paths) >= 5:  # Limit to 5 shortest paths
                    break
        except:
            # Fallback to single path
            try:
                path = nx.shortest_path(G, src, dst, weight='cost')
                paths.append(path)
            except:
                continue
        all_paths[dst] = paths
    
    # Initialize partition assignments
    assignments = {dst: [[] for _ in range(num_partitions)] for dst in dsts}
    
    # Assign partitions round-robin to different paths
    for dst in dsts:
        if dst not in all_paths:
            continue
        paths = all_paths[dst]
        if not paths:
            continue
            
        # Weight paths by inverse cost for better distribution
        path_costs = []
        for path in paths:
            cost = sum(G[path[i]][path[i + 1]]['cost'] for i in range(len(path) - 1))
            path_costs.append(cost)
        
        # Assign partitions
        for p in range(num_partitions):
            # Use weighted random selection
            if len(paths) > 1:
                # Favor cheaper paths but with some randomness
                weights = [1.0 / (c + 0.1) for c in path_costs]
                total = sum(weights)
                if total > 0:
                    r = random.random() * total
                    cum = 0
                    for i, w in enumerate(weights):
                        cum += w
                        if r <= cum:
                            selected_path = paths[i]
                            break
                    else:
                        selected_path = paths[0]
                else:
                    selected_path = paths[p % len(paths)]
            else:
                selected_path = paths[0]
            
            # Store the path
            assignments[dst][p] = selected_path
    
    # Phase 3: Refine assignments to avoid bottlenecks
    # Estimate node usage
    node_usage = {}
    for dst in dsts:
        for p in range(num_partitions):
            path = assignments[dst][p]
            if not path:
                continue
            for node in path:
                node_usage[node] = node_usage.get(node, 0) + 1
    
    # Identify potentially overloaded nodes
    high_usage_nodes = [node for node, usage in node_usage.items() 
                       if usage > num_partitions * 0.3]
    
    # Try to reroute partitions away from overloaded nodes
    for iteration in range(3):  # Limited iterations
        improved = False
        for dst in dsts:
            for p in range(num_partitions):
                current_path = assignments[dst][p]
                if not current_path:
                    continue
                
                # Check if path uses overloaded nodes
                overloaded = any(node in high_usage_nodes for node in current_path)
                if not overloaded:
                    continue
                
                # Try alternative paths
                if dst in all_paths and len(all_paths[dst]) > 1:
                    for alt_path in all_paths[dst]:
                        if alt_path == current_path:
                            continue
                        
                        # Check if alternative is better
                        alt_overloaded = any(node in high_usage_nodes for node in alt_path)
                        if not alt_overloaded:
                            # Switch to alternative
                            assignments[dst][p] = alt_path
                            improved = True
                            break
        if not improved:
            break
    
    # Phase 4: Build final topology
    for dst in dsts:
        for p in range(num_partitions):
            path = assignments[dst][p]
            if not path:
                # Fallback: use any available path
                try:
                    path = nx.shortest_path(G, src, dst, weight='cost')
                except:
                    continue
            
            # Add edges to topology
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = G[u][v]
                bc_topology.append_dst_partition_path(dst, p, [u, v, edge_data])
    
    return bc_topology
'''
        
        return {"code": algorithm_code}
