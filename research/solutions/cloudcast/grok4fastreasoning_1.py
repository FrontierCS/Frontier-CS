class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import networkx as nx
from collections import defaultdict

def get_provider(node):
    return node.split(':')[0]

def compute_total_cost(bc_topology, G, num_partitions, src, dsts):
    if num_partitions == 0:
        return 0.0
    s = 1.0 / num_partitions
    ingress_limits = {"aws":10, "gcp":16, "azure":16}
    egress_limits = {"aws":5, "gcp":7, "azure":16}
    num_vms = 2
    r_instance = 0.54
    P = defaultdict(int)
    all_nodes = set()
    valid = True
    for dst in bc_topology.dsts:
        for p_str, path in bc_topology.paths[dst].items():
            if path is None:
                valid = False
                break
            current = src
            nodes_in_path = set()
            for edge in path:
                u, v, data = edge
                if u != current:
                    valid = False
                    break
                P[(u, v)] += 1
                nodes_in_path.add(u)
                nodes_in_path.add(v)
                current = v
            if current != dst:
                valid = False
                break
            all_nodes.update(nodes_in_path)
        if not valid:
            break
    if not valid:
        return float('inf')
    all_nodes.update([src] + dsts)
    out_used_count = {node: 0 for node in all_nodes}
    in_used_count = {node: 0 for node in all_nodes}
    for (u, v), cnt in P.items():
        if cnt > 0:
            out_used_count[u] += 1
            in_used_count[v] += 1
    f = {}
    for (u, v) in list(P):
        if P[(u, v)] == 0:
            continue
        prov_u = get_provider(u)
        num_out_u = out_used_count[u]
        eff_out = egress_limits[prov_u] * num_vms / num_out_u if num_out_u > 0 else float('inf')
        prov_v = get_provider(v)
        num_in_v = in_used_count[v]
        eff_in = ingress_limits[prov_v] * num_vms / num_in_v if num_in_v > 0 else float('inf')
        thru = G[u][v]['throughput']
        fe = min(eff_out, eff_in, thru)
        if fe <= 0:
            return float('inf')
        f[(u, v)] = fe
    total_path = 0.0
    for (u, v), pe in P.items():
        total_path += pe * G[u][v]['cost']
    C_egress = s * total_path
    t_transfer = 0.0
    for dst in bc_topology.dsts:
        for p_str in bc_topology.paths[dst]:
            path = bc_topology.paths[dst][p_str]
            path_t = 0.0
            for edge in path:
                u, v, _ = edge
                pe = P[(u, v)]
                fe = f[(u, v)]
                t_e = (pe * s * 8) / fe
                path_t = max(path_t, t_e)
            t_transfer = max(t_transfer, path_t)
    num_v = len(all_nodes)
    C_instance = num_v * num_vms * (r_instance / 3600.0) * t_transfer
    return C_egress + C_instance

def assign_with_lambda(lam, src, dsts, G, num_partitions):
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    current_P = defaultdict(int)
    dst_list = list(dsts)
    for part in range(num_partitions):
        for dst in dst_list:
            def edge_weight(u, v, data):
                return data['cost'] + lam * current_P[(u, v)]
            path_nodes = nx.dijkstra_path(G, src, dst, weight=edge_weight)
            path_edges = [[path_nodes[j], path_nodes[j+1], G[path_nodes[j]][path_nodes[j+1]]] for j in range(len(path_nodes)-1)]
            bc_topology.set_dst_partition_paths(dst, part, path_edges)
            for u, v, _ in path_edges:
                current_P[(u, v)] += 1
    return bc_topology

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    if num_partitions == 0:
        return BroadCastTopology(src, dsts, 0)
    lambdas_to_try = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
    best_cost = float('inf')
    best_topology = None
    for lam in lambdas_to_try:
        topo = assign_with_lambda(lam, src, dsts, G, num_partitions)
        cost = compute_total_cost(topo, G, num_partitions, src, dsts)
        if cost < best_cost:
            best_cost = cost
            best_topology = topo
    if best_topology is None:
        best_topology = assign_with_lambda(0.0, src, dsts, G, num_partitions)
    return best_topology
"""
        return {"code": code}