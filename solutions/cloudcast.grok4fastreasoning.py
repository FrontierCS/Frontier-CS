from collections import defaultdict
import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import networkx as nx
from collections import defaultdict

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> 'BroadCastTopology':
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Compute average cost for beta
    all_costs = [G[u][v]['cost'] for u in G for v in G[u]]
    beta = sum(all_costs) / len(all_costs) if all_costs else 1.0
    
    load = defaultdict(int)
    
    for dst in dsts:
        for partition in range(num_partitions):
            def temp_weight(u, v, d):
                return d['cost'] + beta * load[(u, v)]
            
            try:
                path = nx.shortest_path(G, src, dst, weight=temp_weight)
            except nx.NetworkXNoPath:
                # Fallback to min cost path
                path = nx.shortest_path(G, src, dst, weight='cost')
            
            # Convert to edges
            edges = []
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                edge_data = G[u][v]
                edges.append([u, v, edge_data])
            
            bc_topology.set_dst_partition_paths(dst, partition, edges)
            
            # Update loads
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                load[(u, v)] += 1
    
    return bc_topology
"""
        return {"code": code}
