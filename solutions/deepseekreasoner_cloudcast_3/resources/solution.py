import json
import heapq
import math
import random
from collections import defaultdict, deque
import networkx as nx
from typing import List, Dict, Tuple, Set

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

class MultiCommodityFlowSolver:
    def __init__(self, src, dsts, G, num_partitions, ingress_limits, egress_limits, num_vms=2):
        self.src = src
        self.dsts = dsts
        self.G = G.copy()
        self.num_partitions = num_partitions
        self.ingress_limits = ingress_limits
        self.egress_limits = egress_limits
        self.num_vms = num_vms
        
        # Precompute provider from node name
        self.node_provider = {}
        for node in G.nodes():
            provider = node.split(':')[0]
            self.node_provider[node] = provider
            
        # Initialize flow tracking
        self.edge_flows = defaultdict(int)  # partitions per edge
        self.node_in_flows = defaultdict(int)  # partitions entering node
        self.node_out_flows = defaultdict(int)  # partitions leaving node
        
    def get_node_limit(self, node, limit_type):
        """Get bandwidth limit for a node based on its provider"""
        provider = self.node_provider[node]
        limit = self.ingress_limits[provider] if limit_type == 'ingress' else self.egress_limits[provider]
        return limit * self.num_vms
    
    def compute_path_cost(self, path):
        """Compute cost of a path"""
        cost = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            cost += self.G[u][v]['cost']
        return cost
    
    def estimate_congestion_penalty(self, path):
        """Estimate congestion penalty for adding this path"""
        penalty = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            
            # Edge congestion
            current_flow = self.edge_flows[(u, v)] + 1
            capacity = self.G[u][v]['throughput']
            if capacity > 0:
                penalty += (current_flow / capacity) * 10
            
            # Node egress congestion (from u)
            out_flow = self.node_out_flows[u] + 1
            egress_limit = self.get_node_limit(u, 'egress')
            if egress_limit > 0:
                penalty += (out_flow / egress_limit) * 5
            
            # Node ingress congestion (to v)
            in_flow = self.node_in_flows[v] + 1
            ingress_limit = self.get_node_limit(v, 'ingress')
            if ingress_limit > 0:
                penalty += (in_flow / ingress_limit) * 5
                
        return penalty
    
    def update_flows(self, path, delta=1):
        """Update flow counts for a path"""
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            self.edge_flows[(u, v)] += delta
            self.node_out_flows[u] += delta
            self.node_in_flows[v] += delta
    
    def find_k_shortest_paths(self, src, dst, k=5):
        """Find k shortest paths using Yen's algorithm"""
        try:
            paths = list(nx.shortest_simple_paths(self.G, src, dst, weight='cost'))
            return paths[:k]
        except:
            # Fallback to BFS if no path found
            try:
                return [nx.shortest_path(self.G, src, dst)]
            except:
                return []
    
    def find_balanced_path(self, src, dst, partition_id):
        """Find a balanced path considering congestion"""
        best_path = None
        best_score = float('inf')
        
        # Try k-shortest paths
        candidate_paths = self.find_k_shortest_paths(src, dst, k=3)
        
        if not candidate_paths:
            # Try any path
            try:
                candidate_paths = [nx.shortest_path(self.G, src, dst)]
            except:
                return None
        
        for path in candidate_paths:
            cost = self.compute_path_cost(path)
            congestion = self.estimate_congestion_penalty(path)
            score = cost + congestion
            
            if score < best_score:
                best_score = score
                best_path = path
        
        return best_path
    
    def solve_iterative(self):
        """Solve using iterative load balancing"""
        topology = BroadCastTopology(self.src, self.dsts, self.num_partitions)
        
        # First pass: assign all partitions using shortest paths
        for dst in self.dsts:
            for pid in range(self.num_partitions):
                try:
                    path = nx.shortest_path(self.G, self.src, dst, weight='cost')
                    self.update_flows(path)
                    edges = []
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i + 1]
                        edges.append([u, v, self.G[u][v]])
                    topology.set_dst_partition_paths(dst, pid, edges)
                except:
                    pass
        
        # Second pass: redistribute to balance load
        for iteration in range(2):
            # Reset flows
            self.edge_flows.clear()
            self.node_in_flows.clear()
            self.node_out_flows.clear()
            
            # Redistribute partitions
            for dst in self.dsts:
                # Group partitions by current paths
                partition_paths = {}
                for pid in range(self.num_partitions):
                    if topology.paths[dst][str(pid)]:
                        edges = topology.paths[dst][str(pid)]
                        path = [edges[0][0]] + [e[1] for e in edges]
                        partition_paths[pid] = path
                
                # Reassign partitions one by one
                for pid in range(self.num_partitions):
                    # Find balanced path
                    new_path = self.find_balanced_path(self.src, dst, pid)
                    
                    if new_path:
                        # Update flows
                        if pid in partition_paths:
                            self.update_flows(partition_paths[pid], -1)
                        self.update_flows(new_path, 1)
                        
                        # Update topology
                        edges = []
                        for i in range(len(new_path) - 1):
                            u, v = new_path[i], path[i + 1]
                            edges.append([u, v, self.G[u][v]])
                        topology.set_dst_partition_paths(dst, pid, edges)
        
        return topology

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    # Default bandwidth limits (can be overridden by config)
    ingress_limits = {'aws': 10, 'gcp': 16, 'azure': 16}
    egress_limits = {'aws': 5, 'gcp': 7, 'azure': 16}
    num_vms = 2
    
    solver = MultiCommodityFlowSolver(src, dsts, G, num_partitions, 
                                     ingress_limits, egress_limits, num_vms)
    return solver.solve_iterative()

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Read specification
        if spec_path:
            with open(spec_path, 'r') as f:
                spec = json.load(f)
            
            # Get config files
            config_files = spec.get('config_files', [])
            num_vms = spec.get('num_vms', 2)
            
            # For simplicity, we'll generate code that handles the first config
            # The actual evaluator will run this code on all configs
            if config_files:
                config_path = config_files[0]
                code = f'''
import json
import networkx as nx
from collections import defaultdict
import heapq
import math

# Load configuration
with open("{config_path}", 'r') as f:
    config = json.load(f)

src = config["source_node"]
dsts = config["dest_nodes"]
data_vol = config["data_vol"]
num_partitions = config["num_partitions"]
ingress_limits = config["ingress_limit"]
egress_limits = config["egress_limit"]

# The actual graph G will be provided by the evaluator
def search_algorithm(src, dsts, G, num_partitions):
    # Use the solver defined below
    solver = MultiCommodityFlowSolver(src, dsts, G, num_partitions, 
                                     ingress_limits, egress_limits, {num_vms})
    return solver.solve_iterative()

# Include all the helper classes and functions
{inspect.getsource(MultiCommodityFlowSolver.__init__)}
{inspect.getsource(MultiCommodityFlowSolver.get_node_limit)}
{inspect.getsource(MultiCommodityFlowSolver.compute_path_cost)}
{inspect.getsource(MultiCommodityFlowSolver.estimate_congestion_penalty)}
{inspect.getsource(MultiCommodityFlowSolver.update_flows)}
{inspect.getsource(MultiCommodityFlowSolver.find_k_shortest_paths)}
{inspect.getsource(MultiCommodityFlowSolver.find_balanced_path)}
{inspect.getsource(MultiCommodityFlowSolver.solve_iterative)}
'''
            else:
                code = f'''
def search_algorithm(src, dsts, G, num_partitions):
    # Default implementation
    ingress_limits = {{'aws': 10, 'gcp': 16, 'azure': 16}}
    egress_limits = {{'aws': 5, 'gcp': 7, 'azure': 16}}
    num_vms = {num_vms}
    
    solver = MultiCommodityFlowSolver(src, dsts, G, num_partitions, 
                                     ingress_limits, egress_limits, num_vms)
    return solver.solve_iterative()

# Include all the helper classes and functions
{inspect.getsource(MultiCommodityFlowSolver.__init__)}
{inspect.getsource(MultiCommodityFlowSolver.get_node_limit)}
{inspect.getsource(MultiCommodityFlowSolver.compute_path_cost)}
{inspect.getsource(MultiCommodityFlowSolver.estimate_congestion_penalty)}
{inspect.getsource(MultiCommodityFlowSolver.update_flows)}
{inspect.getsource(MultiCommodityFlowSolver.find_k_shortest_paths)}
{inspect.getsource(MultiCommodityFlowSolver.find_balanced_path)}
{inspect.getsource(MultiCommodityFlowSolver.solve_iterative)}
'''
        else:
            code = f'''
def search_algorithm(src, dsts, G, num_partitions):
    # Default implementation
    ingress_limits = {{'aws': 10, 'gcp': 16, 'azure': 16}}
    egress_limits = {{'aws': 5, 'gcp': 7, 'azure': 16}}
    num_vms = 2
    
    solver = MultiCommodityFlowSolver(src, dsts, G, num_partitions, 
                                     ingress_limits, egress_limits, num_vms)
    return solver.solve_iterative()

# Include all the helper classes and functions
{inspect.getsource(MultiCommodityFlowSolver.__init__)}
{inspect.getsource(MultiCommodityFlowSolver.get_node_limit)}
{inspect.getsource(MultiCommodityFlowSolver.compute_path_cost)}
{inspect.getsource(MultiCommodityFlowSolver.estimate_congestion_penalty)}
{inspect.getsource(MultiCommodityFlowSolver.update_flows)}
{inspect.getsource(MultiCommodityFlowSolver.find_k_shortest_paths)}
{inspect.getsource(MultiCommodityFlowSolver.find_balanced_path)}
{inspect.getsource(MultiCommodityFlowSolver.solve_iterative)}
'''
        
        return {"code": code}

# Helper to get source code of classes/functions
import inspect
