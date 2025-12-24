import networkx as nx
from collections import defaultdict
import random
import textwrap

class BroadCastTopology:
    """
    A class to store and manage broadcast topology paths.
    This class is provided in the evaluation environment, but included here
    for completeness and to satisfy the API implementation requirement.
    """
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
        # Each edge is [src_node, dst_node, edge_data_dict]
        self.paths = {dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts}

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        """
        Append an edge to the path for a specific destination-partition pair.
        """
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
        """
        Set the complete path (list of edges) for a destination-partition pair.
        """
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        """Update number of partitions"""
        self.num_partitions = num_partitions


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    This function is a placeholder here, as the actual code is provided as a string
    by the Solution.solve() method. The implementation is identical to the one
    in the string below.
    """
    pass


class Solution:
    """
    The main solution class for the Cloudcast Broadcast Optimization Problem.
    """
    def solve(self, spec_path: str = None) -> dict:
        """
        Provides the broadcast optimization algorithm as a Python code string.
        
        The method packages the source code of the `search_algorithm` and its
        dependencies into a dictionary, which is then used by the evaluator.
        """
        
        algorithm_code = """
import networkx as nx
from collections import defaultdict
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
    G.graph.setdefault('data_vol', 300)
    G.graph.setdefault('num_vms', 2)
    G.graph.setdefault('ingress_limit', {"aws": 10, "gcp": 16, "azure": 16})
    G.graph.setdefault('egress_limit', {"aws": 5, "gcp": 7, "azure": 16})

    data_vol = G.graph['data_vol']
    num_vms = G.graph['num_vms']
    ingress_limit = G.graph['ingress_limit']
    egress_limit = G.graph['egress_limit']

    s_partition = data_vol / num_partitions if num_partitions > 0 else 0
    r_instance = 0.54

    V_est = len(dsts) + 10
    C_TIME = V_est * num_vms * r_instance / 3600.0

    edge_counts = defaultdict(int)
    used_edges = set()
    node_out_counts = defaultdict(int)
    node_in_counts = defaultdict(int)

    topology = BroadCastTopology(src, dsts, num_partitions)

    tasks = [(p, d) for p in range(num_partitions) for d in dsts]
    random.seed(42)
    random.shuffle(tasks)

    for p, d in tasks:
        def weight_func(u, v, edge_data):
            edge = (u, v)
            provider_u = u.split(':')[0]
            provider_v = v.split(':')[0]

            deg_out = node_out_counts[u] or 1
            deg_in = node_in_counts[v] or 1
            
            egress_cap = egress_limit[provider_u] * num_vms / deg_out
            ingress_cap = ingress_limit[provider_v] * num_vms / deg_in
            
            f_e = min(edge_data['throughput'], egress_cap, ingress_cap)
            
            if f_e <= 1e-9:
                return float('inf')

            cost_on_edge = s_partition * edge_data['cost']
            time_on_edge = (edge_counts[edge] + 1) * s_partition * 8 / f_e
            
            return cost_on_edge + C_TIME * time_on_edge

        try:
            path_nodes = nx.dijkstra_path(G, src, d, weight=weight_func)
        except nx.NetworkXNoPath:
            path_nodes = nx.dijkstra_path(G, src, d, weight="cost")
        
        path_edges = []
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edge = (u, v)
            
            path_edges.append([u, v, G[u][v]])
            
            edge_counts[edge] += 1
            if edge not in used_edges:
                used_edges.add(edge)
                node_out_counts[u] += 1
                node_in_counts[v] += 1
        
        topology.set_dst_partition_paths(d, p, path_edges)
        
    return topology
"""
        return {"code": textwrap.dedent(algorithm_code).strip()}
