import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import networkx as nx

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> 'BroadCastTopology':
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # Initialize current weights
    current_weights = {}
    all_costs = []
    for u in G.nodes():
        for v in G.successors(u):
            edge_key = (u, v)
            current_weights[edge_key] = G[u][v]['cost']
            all_costs.append(G[u][v]['cost'])
    
    if all_costs:
        avg_cost = sum(all_costs) / len(all_costs)
        penalty = 0.1 * avg_cost
    else:
        penalty = 0.01
    
    def weight_func(u, v, data):
        key = (u, v)
        return current_weights.get(key, float('inf'))
    
    for pid in range(num_partitions):
        try:
            path_dict = nx.single_source_dijkstra_path(G, src, weight=weight_func)
            used_edges_this_partition = set()
            for dst in dsts:
                if dst not in path_dict:
                    continue
                node_path = path_dict[dst]
                if len(node_path) < 2 or node_path[0] != src or node_path[-1] != dst:
                    continue
                edge_list = []
                for i in range(len(node_path) - 1):
                    uu = node_path[i]
                    vv = node_path[i + 1]
                    edge_data = G[uu][vv]
                    edge_list.append([uu, vv, edge_data])
                    used_edges_this_partition.add((uu, vv))
                bc_topology.set_dst_partition_paths(dst, pid, edge_list)
            # Penalize unique edges used by this partition
            for ue in used_edges_this_partition:
                if ue in current_weights:
                    current_weights[ue] += penalty
        except:
            # Fallback to basic if dijkstra fails
            for dst in dsts:
                try:
                    basic_path = nx.dijkstra_path(G, src, dst, weight='cost')
                    edge_list = []
                    for i in range(len(basic_path) - 1):
                        uu = basic_path[i]
                        vv = basic_path[i + 1]
                        edge_data = G[uu][vv]
                        edge_list.append([uu, vv, edge_data])
                    bc_topology.set_dst_partition_paths(dst, pid, edge_list)
                except:
                    pass
    
    return bc_topology
"""
        return {"code": code}
