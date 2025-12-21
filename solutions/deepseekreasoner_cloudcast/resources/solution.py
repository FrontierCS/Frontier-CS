import json
import networkx as nx
from collections import defaultdict
import heapq
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import json
import networkx as nx
from collections import defaultdict
import heapq
import math

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    if not dsts:
        return bc_topology
        
    # Provider mapping from node names
    def get_provider(node):
        return node.split(':')[0].lower() if ':' in node else ''
    
    # Find multiple shortest paths for each destination
    for dst in dsts:
        # Use Yen's algorithm to find k shortest paths
        k = min(5, num_partitions)  # Find up to 5 different paths per destination
        try:
            paths = list(nx.shortest_simple_paths(G, src, dst, weight='cost'))
            paths = list(paths)[:k]
        except:
            # Fallback to single shortest path
            try:
                path = nx.dijkstra_path(G, src, dst, weight='cost')
                paths = [path]
            except:
                continue
        
        if not paths:
            continue
            
        # Assign partitions to paths in round-robin fashion
        for i in range(num_partitions):
            path_idx = i % len(paths)
            path = paths[path_idx]
            
            # Build edge list for this path
            edge_list = []
            for j in range(len(path) - 1):
                u, v = path[j], path[j + 1]
                edge_data = G[u][v]
                edge_list.append([u, v, edge_data])
            
            bc_topology.set_dst_partition_paths(dst, i, edge_list)
    
    return bc_topology

def load_ingress_egress_limits(config_files):
    ingress_limits = {'aws': 10, 'gcp': 16, 'azure': 16}
    egress_limits = {'aws': 5, 'gcp': 7, 'azure': 16}
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if 'ingress_limit' in config:
                    ingress_limits.update(config['ingress_limit'])
                if 'egress_limit' in config:
                    egress_limits.update(config['egress_limit'])
        except:
            continue
    
    return ingress_limits, egress_limits

def compute_bandwidth_constrained_flow(paths_dict, G, ingress_limits, egress_limits, num_vms=2):
    # Count partitions per edge
    edge_partition_count = defaultdict(int)
    node_in_edges = defaultdict(list)
    node_out_edges = defaultdict(list)
    
    for dst in paths_dict:
        for partition in paths_dict[dst]:
            path = paths_dict[dst][partition]
            if path:
                for edge in path:
                    u, v, _ = edge
                    edge_key = (u, v)
                    edge_partition_count[edge_key] += 1
                    node_out_edges[u].append(edge_key)
                    node_in_edges[v].append(edge_key)
    
    # Compute actual throughput per edge considering node constraints
    edge_throughput = {}
    
    for u in node_out_edges:
        provider_u = u.split(':')[0].lower() if ':' in u else ''
        if provider_u in egress_limits:
            egress_capacity = egress_limits[provider_u] * num_vms
            out_count = len(set(node_out_edges[u]))
            if out_count > 0:
                per_edge_egress = egress_capacity / out_count
                for edge_key in set(node_out_edges[u]):
                    if edge_key in G[u][edge_key[1]]:
                        edge_max = G[u][edge_key[1]].get('throughput', float('inf'))
                        edge_throughput[edge_key] = min(edge_max, per_edge_egress)
    
    for v in node_in_edges:
        provider_v = v.split(':')[0].lower() if ':' in v else ''
        if provider_v in ingress_limits:
            ingress_capacity = ingress_limits[provider_v] * num_vms
            in_count = len(set(node_in_edges[v]))
            if in_count > 0:
                per_edge_ingress = ingress_capacity / in_count
                for edge_key in set(node_in_edges[v]):
                    if edge_key in edge_throughput:
                        edge_throughput[edge_key] = min(edge_throughput[edge_key], per_edge_ingress)
    
    return edge_partition_count, edge_throughput

def compute_transfer_time(edge_partition_count, edge_throughput, s_partition):
    max_time = 0
    for edge_key, partition_count in edge_partition_count.items():
        if partition_count > 0 and edge_key in edge_throughput:
            throughput = edge_throughput[edge_key]
            if throughput > 0:
                edge_time = (partition_count * s_partition * 8) / throughput
                max_time = max(max_time, edge_time)
    return max_time

def compute_total_cost(config_files, num_vms=2):
    total_cost = 0
    total_transfer_time = 0
    
    # Process each config file
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except:
            continue
            
        source = config.get('source_node', '')
        destinations = config.get('dest_nodes', [])
        data_vol = config.get('data_vol', 100)
        num_partitions = config.get('num_partitions', 1)
        s_partition = data_vol / num_partitions if num_partitions > 0 else 0
        
        ingress_limits = config.get('ingress_limit', {'aws': 10, 'gcp': 16, 'azure': 16})
        egress_limits = config.get('egress_limit', {'aws': 5, 'gcp': 7, 'azure': 16})
        
        # Create graph from config (simplified - in real implementation, G would be provided)
        # This is placeholder for cost calculation logic
        
    return total_cost

if __name__ == "__main__":
    # This function would be called by the evaluator
    pass'''
        
        return {"code": code}
