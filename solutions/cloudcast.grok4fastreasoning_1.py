class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import networkx as nx
from collections import defaultdict

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    flow = defaultdict(int)
    gamma = 0.05
    for partition in range(num_partitions):
        for dst in dsts:
            def weight_func(u, v):
                base = G[u][v]['cost']
                penalty = gamma * flow[(u, v)]
                return base + penalty
            try:
                path_nodes = nx.dijkstra_path(G, src, dst, weight=weight_func)
                path_edges = []
                for i in range(len(path_nodes) - 1):
                    u = path_nodes[i]
                    v = path_nodes[i + 1]
                    edge_data = G[u][v]
                    path_edges.append([u, v, edge_data])
                    flow[(u, v)] += 1
                bc_topology.set_dst_partition_paths(dst, partition, path_edges)
            except nx.NetworkXNoPath:
                pass
    return bc_topology
"""
        return {"code": code}
