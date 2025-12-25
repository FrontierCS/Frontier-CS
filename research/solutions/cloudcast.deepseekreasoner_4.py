import networkx as nx
import json
import math
from typing import Dict, List, Set, Tuple
import heapq
from collections import defaultdict, deque

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> "BroadCastTopology":
    """
    Optimized broadcast routing algorithm that minimizes total cost while respecting bandwidth constraints.
    Uses multi-path routing with load balancing across partitions.
    """
    
    class NodeLimits:
        """Helper class to manage node bandwidth constraints"""
        def __init__(self, provider: str, num_vms: int = 2):
            self.provider = provider
            self.num_vms = num_vms
            # Default limits based on provider
            if provider == "aws":
                self.ingress = 10 * num_vms  # Gbps
                self.egress = 5 * num_vms
            elif provider == "gcp":
                self.ingress = 16 * num_vms
                self.egress = 7 * num_vms
            elif provider == "azure":
                self.ingress = 16 * num_vms
                self.egress = 16 * num_vms
            else:
                # Fallback defaults
                self.ingress = 10 * num_vms
                self.egress = 5 * num_vms
    
    def get_provider(node: str) -> str:
        """Extract provider from node string (e.g., 'aws:us-east-1' -> 'aws')"""
        return node.split(":")[0]
    
    def yen_k_shortest_paths(graph, source, target, k=3, weight='cost'):
        """Find k shortest paths using Yen's algorithm"""
        paths = []
        
        # First shortest path
        try:
            first_path = nx.shortest_path(graph, source, target, weight=weight)
            paths.append(first_path)
        except nx.NetworkXNoPath:
            return []
        
        # Potential paths
        potential_paths = []
        
        for i in range(1, k):
            for j in range(len(paths[i-1]) - 1):
                spur_node = paths[i-1][j]
                root_path = paths[i-1][:j+1]
                
                # Create a copy of the graph
                graph_copy = graph.copy()
                
                # Remove edges used in previous paths that share the root path
                for path in paths:
                    if len(path) > j and root_path == path[:j+1]:
                        if j+1 < len(path):
                            if graph_copy.has_edge(path[j], path[j+1]):
                                graph_copy.remove_edge(path[j], path[j+1])
                
                # Remove nodes from root path (except spur node)
                for node in root_path[:-1]:
                    if node in graph_copy:
                        graph_copy.remove_node(node)
                
                # Find spur path
                try:
                    spur_path = nx.shortest_path(graph_copy, spur_node, target, weight=weight)
                    
                    # Combine root path and spur path
                    total_path = root_path[:-1] + spur_path
                    
                    # Check if path is valid
                    if total_path not in paths and total_path not in [p[1] for p in potential_paths]:
                        path_cost = sum(graph[u][v]['cost'] for u, v in zip(total_path[:-1], total_path[1:]))
                        heapq.heappush(potential_paths, (path_cost, total_path))
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
            
            if not potential_paths:
                break
                
            # Get the next best path
            _, next_path = heapq.heappop(potential_paths)
            paths.append(next_path)
        
        return paths
    
    def compute_edge_utilization(paths_dict, num_partitions):
        """Compute how many partitions use each edge"""
        edge_usage = defaultdict(int)
        
        for dst in dsts:
            for partition in range(num_partitions):
                partition_str = str(partition)
                if dst in paths_dict and partition_str in paths_dict[dst]:
                    path_edges = paths_dict[dst][partition_str]
                    if path_edges:
                        for edge in path_edges:
                            if len(edge) >= 2:
                                src_node, dst_node = edge[0], edge[1]
                                edge_usage[(src_node, dst_node)] += 1
        
        return edge_usage
    
    def estimate_transfer_time(edge_usage, partition_size_gb, node_limits):
        """Estimate transfer time considering bandwidth constraints"""
        if not edge_usage:
            return 0.0
        
        # First pass: compute node degrees
        node_out_degree = defaultdict(int)
        node_in_degree = defaultdict(int)
        
        for (u, v) in edge_usage.keys():
            node_out_degree[u] += 1
            node_in_degree[v] += 1
        
        # Compute maximum flow per edge considering node constraints
        max_edge_throughput = {}
        
        for (u, v) in edge_usage.keys():
            # Edge's own throughput
            edge_throughput = G[u][v].get('throughput', float('inf'))
            
            # Node egress constraint for u
            u_provider = get_provider(u)
            u_egress_limit = node_limits[u_provider].egress
            u_out_deg = max(1, node_out_degree[u])
            egress_limit_per_edge = u_egress_limit / u_out_deg
            
            # Node ingress constraint for v
            v_provider = get_provider(v)
            v_ingress_limit = node_limits[v_provider].ingress
            v_in_deg = max(1, node_in_degree[v])
            ingress_limit_per_edge = v_ingress_limit / v_in_deg
            
            # Effective throughput is min of all constraints
            max_edge_throughput[(u, v)] = min(
                edge_throughput,
                egress_limit_per_edge,
                ingress_limit_per_edge
            )
        
        # Compute transfer time for each edge
        max_time = 0.0
        for (u, v), usage_count in edge_usage.items():
            if usage_count > 0 and max_edge_throughput[(u, v)] > 0:
                # Data in bits: usage_count * partition_size_gb * 8
                data_bits = usage_count * partition_size_gb * 8
                time_needed = data_bits / max_edge_throughput[(u, v)]
                max_time = max(max_time, time_needed)
        
        return max_time
    
    # Create broadcast topology
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # For small networks or few partitions, use simple approach
    if len(G.nodes()) <= 10 or num_partitions <= 3:
        # Use simple Dijkstra for each destination
        for dst in dsts:
            try:
                path = nx.shortest_path(G, src, dst, weight='cost')
                for partition_id in range(num_partitions):
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        edge_data = G[u][v]
                        bc_topology.append_dst_partition_path(dst, partition_id, [u, v, edge_data])
            except nx.NetworkXNoPath:
                # If no path exists, try to find any path ignoring cost
                try:
                    path = nx.shortest_path(G, src, dst)
                    for partition_id in range(num_partitions):
                        for i in range(len(path) - 1):
                            u, v = path[i], path[i+1]
                            edge_data = G[u][v]
                            bc_topology.append_dst_partition_path(dst, partition_id, [u, v, edge_data])
                except nx.NetworkXNoPath:
                    continue
        return bc_topology
    
    # Initialize node limits
    node_limits = {}
    for provider in ["aws", "gcp", "azure"]:
        node_limits[provider] = NodeLimits(provider)
    
    # Strategy: Use multiple paths per destination with load balancing
    # Find up to 3 shortest paths per destination
    paths_per_dst = {}
    max_paths_per_dst = min(3, num_partitions)  # Don't need more paths than partitions
    
    for dst in dsts:
        k_paths = yen_k_shortest_paths(G, src, dst, k=max_paths_per_dst, weight='cost')
        if k_paths:
            paths_per_dst[dst] = k_paths
        else:
            # Fallback: use any path
            try:
                path = nx.shortest_path(G, src, dst)
                paths_per_dst[dst] = [path]
            except nx.NetworkXNoPath:
                paths_per_dst[dst] = []
    
    # Assign partitions to paths for each destination
    for dst, paths in paths_per_dst.items():
        if not paths:
            # If still no path, skip this destination
            continue
        
        # Simple round-robin assignment
        for partition_id in range(num_partitions):
            path_idx = partition_id % len(paths)
            path = paths[path_idx]
            
            # Add edges to broadcast topology
            edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                edge_data = G[u][v]
                edges.append([u, v, edge_data])
            
            bc_topology.set_dst_partition_paths(dst, partition_id, edges)
    
    # Optimize: Try to share paths for destinations with common prefixes
    # Build a prefix tree to identify common paths
    all_paths = {}
    for dst in dsts:
        for partition in range(num_partitions):
            partition_str = str(partition)
            if dst in bc_topology.paths and partition_str in bc_topology.paths[dst]:
                path_edges = bc_topology.paths[dst][partition_str]
                if path_edges:
                    # Extract node sequence
                    nodes = [path_edges[0][0]]  # Start with source
                    for edge in path_edges:
                        nodes.append(edge[1])
                    all_paths[(dst, partition)] = nodes
    
    # Try to merge paths with common prefixes
    # Group by common intermediate nodes
    common_nodes = defaultdict(list)
    for (dst, partition), nodes in all_paths.items():
        # Use first 3 nodes as key for grouping (if path is long enough)
        if len(nodes) >= 3:
            key = tuple(nodes[:3])  # Source + next 2 hops
            common_nodes[key].append((dst, partition))
    
    # For groups with multiple destinations, ensure they share the same path
    for key, destinations in common_nodes.items():
        if len(destinations) > 1:
            # Choose the lowest cost path among them
            best_path = None
            best_cost = float('inf')
            
            for dst, partition in destinations:
                partition_str = str(partition)
                path_edges = bc_topology.paths[dst][partition_str]
                if path_edges:
                    path_cost = sum(edge[2]['cost'] for edge in path_edges)
                    if path_cost < best_cost:
                        best_cost = path_cost
                        best_path = path_edges
            
            # Apply the best path to all destinations in the group
            if best_path:
                for dst, partition in destinations:
                    bc_topology.set_dst_partition_paths(dst, partition, best_path)
    
    return bc_topology


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the search algorithm code.
        """
        # Get the source code of the search_algorithm function
        import inspect
        code = inspect.getsource(search_algorithm)
        
        # Also include the NodeLimits class
        node_limits_code = """
class NodeLimits:
    def __init__(self, provider: str, num_vms: int = 2):
        self.provider = provider
        self.num_vms = num_vms
        if provider == "aws":
            self.ingress = 10 * num_vms
            self.egress = 5 * num_vms
        elif provider == "gcp":
            self.ingress = 16 * num_vms
            self.egress = 7 * num_vms
        elif provider == "azure":
            self.ingress = 16 * num_vms
            self.egress = 16 * num_vms
        else:
            self.ingress = 10 * num_vms
            self.egress = 5 * num_vms
"""
        
        full_code = node_limits_code + "\n\n" + code
        
        return {"code": full_code}
