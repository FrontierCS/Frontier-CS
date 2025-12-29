import json
import networkx as nx
import heapq
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Set
import random

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
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    node_providers = {node: node.split(':')[0] for node in G.nodes()}
    
    ingress_limits = {'aws': 10, 'gcp': 16, 'azure': 16}
    egress_limits = {'aws': 5, 'gcp': 7, 'azure': 16}
    
    num_vms = 2
    
    for dst in dsts:
        all_paths = []
        
        k = min(5, num_partitions)
        try:
            k_paths = list(nx.shortest_simple_paths(G, src, dst, weight='cost'))[:k]
            all_paths.extend(k_paths)
        except:
            try:
                single_path = nx.shortest_path(G, src, dst, weight='cost')
                all_paths.append(single_path)
            except:
                continue
        
        for partition_id in range(num_partitions):
            if len(all_paths) == 0:
                continue
                
            path_idx = partition_id % len(all_paths)
            path = all_paths[path_idx]
            
            path_edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = G[u][v]
                path_edges.append([u, v, edge_data])
            
            bc_topology.set_dst_partition_paths(dst, partition_id, path_edges)
    
    return bc_topology


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        solution_code = '''
import json
import networkx as nx
import heapq
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Set
import random

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


def calculate_edge_usage(bc_topology: BroadCastTopology) -> Tuple[Dict[Tuple[str, str], int], Set[str]]:
    edge_usage = defaultdict(int)
    used_nodes = set()
    
    for dst in bc_topology.dsts:
        for partition in range(bc_topology.num_partitions):
            path = bc_topology.paths[dst][str(partition)]
            if path is None:
                continue
            for edge in path:
                u, v, _ = edge
                edge_key = (u, v)
                edge_usage[edge_key] += 1
                used_nodes.add(u)
                used_nodes.add(v)
    
    return edge_usage, used_nodes


def calculate_transfer_time(G: nx.DiGraph, edge_usage: Dict[Tuple[str, str], int], 
                           data_vol: float, num_partitions: int,
                           num_vms: int = 2) -> float:
    if not edge_usage:
        return 0.0
    
    s_partition = data_vol / num_partitions
    
    node_out_edges = defaultdict(list)
    node_in_edges = defaultdict(list)
    
    for (u, v) in edge_usage.keys():
        node_out_edges[u].append((u, v))
        node_in_edges[v].append((u, v))
    
    ingress_limits = {'aws': 10, 'gcp': 16, 'azure': 16}
    egress_limits = {'aws': 5, 'gcp': 7, 'azure': 16}
    
    max_edge_time = 0.0
    
    for (u, v), usage_count in edge_usage.items():
        edge_data = G[u][v]
        throughput_capacity = edge_data.get('throughput', float('inf'))
        
        provider_u = u.split(':')[0]
        provider_v = v.split(':')[0]
        
        out_degree = len(node_out_edges[u])
        in_degree = len(node_in_edges[v])
        
        egress_limit = egress_limits.get(provider_u, 16) * num_vms
        ingress_limit = ingress_limits.get(provider_v, 16) * num_vms
        
        effective_egress = egress_limit / max(1, out_degree)
        effective_ingress = ingress_limit / max(1, in_degree)
        
        effective_throughput = min(throughput_capacity, effective_egress, effective_ingress)
        
        if effective_throughput <= 0:
            effective_throughput = 0.001
        
        time_per_edge = (usage_count * s_partition * 8) / effective_throughput
        max_edge_time = max(max_edge_time, time_per_edge)
    
    return max_edge_time


def calculate_cost(G: nx.DiGraph, edge_usage: Dict[Tuple[str, str], int],
                   used_nodes: Set[str], transfer_time: float,
                   data_vol: float, num_partitions: int,
                   num_vms: int = 2, instance_rate: float = 0.54) -> float:
    s_partition = data_vol / num_partitions
    
    egress_cost = 0.0
    for (u, v), usage_count in edge_usage.items():
        edge_data = G[u][v]
        cost_per_gb = edge_data.get('cost', 0.0)
        egress_cost += usage_count * s_partition * cost_per_gb
    
    instance_cost = len(used_nodes) * num_vms * (instance_rate / 3600) * transfer_time
    
    return egress_cost + instance_cost


def find_k_shortest_paths(G: nx.DiGraph, src: str, dst: str, k: int, weight='cost'):
    try:
        return list(nx.shortest_simple_paths(G, src, dst, weight=weight))[:k]
    except:
        try:
            path = nx.shortest_path(G, src, dst, weight=weight)
            return [path]
        except:
            return []


def find_diverse_paths(G: nx.DiGraph, src: str, dst: str, k: int, weight='cost'):
    paths = find_k_shortest_paths(G, src, dst, k, weight)
    
    if len(paths) < k:
        try:
            all_paths = list(nx.all_simple_paths(G, src, dst))
            if weight == 'cost':
                all_paths.sort(key=lambda p: sum(G[p[i]][p[i+1]]['cost'] for i in range(len(p)-1)))
            else:
                all_paths.sort(key=lambda p: sum(1 for _ in range(len(p)-1)))
            
            for path in all_paths:
                if path not in paths:
                    paths.append(path)
                if len(paths) >= k:
                    break
        except:
            pass
    
    return paths[:k]


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    node_providers = {node: node.split(':')[0] for node in G.nodes()}
    
    for dst in dsts:
        k = min(max(3, num_partitions // 2), 10)
        diverse_paths = find_diverse_paths(G, src, dst, k, weight='cost')
        
        if not diverse_paths:
            continue
        
        for partition_id in range(num_partitions):
            path_idx = partition_id % len(diverse_paths)
            path = diverse_paths[path_idx]
            
            path_edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = G[u][v]
                path_edges.append([u, v, edge_data])
            
            bc_topology.set_dst_partition_paths(dst, partition_id, path_edges)
    
    return bc_topology


def optimized_search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, 
                               num_partitions: int, data_vol: float = 300.0,
                               num_vms: int = 2) -> BroadCastTopology:
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    all_dst_paths = {}
    
    for dst in dsts:
        k = min(max(3, num_partitions // 3), 8)
        diverse_paths = find_diverse_paths(G, src, dst, k, weight='cost')
        
        if not diverse_paths:
            try:
                fallback_path = nx.shortest_path(G, src, dst, weight='cost')
                diverse_paths = [fallback_path]
            except:
                continue
        
        path_costs = []
        for path in diverse_paths:
            cost = sum(G[path[i]][path[i+1]]['cost'] for i in range(len(path)-1))
            path_costs.append((cost, path))
        
        path_costs.sort()
        
        all_dst_paths[dst] = [path for _, path in path_costs]
    
    partition_assignments = {}
    for partition_id in range(num_partitions):
        partition_assignments[partition_id] = {}
        for dst in dsts:
            if dst in all_dst_paths and all_dst_paths[dst]:
                path_idx = partition_id % len(all_dst_paths[dst])
                partition_assignments[partition_id][dst] = all_dst_paths[dst][path_idx]
    
    best_topology = None
    best_cost = float('inf')
    
    for iteration in range(20):
        current_bc = BroadCastTopology(src, dsts, num_partitions)
        
        for dst in dsts:
            for partition_id in range(num_partitions):
                if dst in partition_assignments[partition_id]:
                    path = partition_assignments[partition_id][dst]
                    
                    path_edges = []
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i + 1]
                        edge_data = G[u][v]
                        path_edges.append([u, v, edge_data])
                    
                    current_bc.set_dst_partition_paths(dst, partition_id, path_edges)
        
        edge_usage, used_nodes = calculate_edge_usage(current_bc)
        transfer_time = calculate_transfer_time(G, edge_usage, data_vol, num_partitions, num_vms)
        total_cost = calculate_cost(G, edge_usage, used_nodes, transfer_time, 
                                   data_vol, num_partitions, num_vms)
        
        if total_cost < best_cost:
            best_cost = total_cost
            best_topology = current_bc
        
        if iteration < 10:
            for partition_id in range(num_partitions):
                for dst in dsts:
                    if dst in all_dst_paths and len(all_dst_paths[dst]) > 1:
                        current_path = partition_assignments[partition_id].get(dst)
                        if current_path and current_path in all_dst_paths[dst]:
                            current_idx = all_dst_paths[dst].index(current_path)
                            new_idx = (current_idx + 1) % len(all_dst_paths[dst])
                            partition_assignments[partition_id][dst] = all_dst_paths[dst][new_idx]
    
    if best_topology is None:
        return search_algorithm(src, dsts, G, num_partitions)
    
    return best_topology


def final_search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    try:
        with open('/tmp/config_cache.json', 'r') as f:
            config_cache = json.load(f)
            data_vol = config_cache.get('data_vol', 300.0)
            num_vms = config_cache.get('num_vms', 2)
    except:
        data_vol = 300.0
        num_vms = 2
    
    return optimized_search_algorithm(src, dsts, G, num_partitions, data_vol, num_vms)
'''
        return {"code": solution_code}