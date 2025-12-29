class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import networkx as nx
from collections import defaultdict

ingress_limits = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
egress_limits = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}
n_vm = 2.0
lambda_ = n_vm * 0.54 / 3600 * 8

def get_provider(node):
    if ':' not in node:
        return "unknown"
    return node.split(':', 1)[0]

def get_ingress(node):
    prov = get_provider(node)
    return ingress_limits.get(prov, 100.0) * n_vm

def get_egress(node):
    prov = get_provider(node)
    return egress_limits.get(prov, 100.0) * n_vm

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> 'BroadCastTopology':
    bc = BroadCastTopology(src, dsts, num_partitions)
    flow = defaultdict(int)
    used_out = defaultdict(set)
    used_in = defaultdict(set)
    used_nodes = set()
    current_egress = 0.0
    current_max_load = 0.0
    current_V = 0
    for dst in dsts:
        for pid in range(num_partitions):
            candidates = []
            try:
                path_gen = nx.shortest_simple_paths(G, src, dst, weight='cost')
                for _ in range(5):
                    try:
                        node_path = next(path_gen)
                        path_edges = [(node_path[j], node_path[j+1]) for j in range(len(node_path)-1)]
                        candidates.append(path_edges)
                    except StopIteration:
                        break
            except:
                pass
            if not candidates:
                continue
            best_score = float('inf')
            best_path_edges = None
            for path_edges in candidates:
                path_set = set(path_edges)
                path_nodes = set(u for u, v in path_edges) | set(v for u, v in path_edges)
                delta_egress = sum(G.get(u, {}).get(v, {}).get('cost', 0) for u, v in path_edges)
                new_egress = current_egress + delta_egress
                new_used_nodes = used_nodes | path_nodes
                new_V_len = len(new_used_nodes)
                new_used_out_temp = {n: used_out[n].copy() for n in used_out}
                new_used_in_temp = {n: used_in[n].copy() for n in used_in}
                affected_out_temp = set()
                affected_in_temp = set()
                for u, v in path_edges:
                    was_used = flow[(u, v)] > 0
                    if not was_used:
                        if v not in new_used_out_temp.get(u, set()):
                            new_used_out_temp.setdefault(u, set()).add(v)
                            affected_out_temp.add(u)
                        if u not in new_used_in_temp.get(v, set()):
                            new_used_in_temp.setdefault(v, set()).add(u)
                            affected_in_temp.add(v)
                checked = set(path_edges)
                for u in affected_out_temp:
                    for vv in new_used_out_temp.get(u, set()):
                        checked.add((u, vv))
                for v in affected_in_temp:
                    for uu in new_used_in_temp.get(v, set()):
                        checked.add((uu, v))
                max_checked_load = 0.0
                for e in checked:
                    uu, vv = e
                    add1 = 1 if e in path_set else 0
                    new_fl = flow[e] + add1
                    if new_fl == 0:
                        continue
                    new_k_u = len(new_used_out_temp.get(uu, set()))
                    cap_eg = get_egress(uu) / new_k_u if new_k_u > 0 else float('inf')
                    new_m_v = len(new_used_in_temp.get(vv, set()))
                    cap_in = get_ingress(vv) / new_m_v if new_m_v > 0 else float('inf')
                    thru = G.get(uu, {}).get(vv, {}).get('throughput', float('inf'))
                    new_f = min(thru, cap_eg, cap_in)
                    new_load = new_fl / new_f if new_f > 0 else float('inf')
                    if new_load > max_checked_load:
                        max_checked_load = new_load
                new_max_load = max(current_max_load, max_checked_load)
                new_effective = new_egress + lambda_ * new_V_len * new_max_load
                if new_effective < best_score:
                    best_score = new_effective
                    best_path_edges = path_edges
            if best_path_edges is not None:
                path_set = set(best_path_edges)
                path_nodes = set(u for u, v in best_path_edges) | set(v for u, v in best_path_edges)
                used_nodes |= path_nodes
                current_V = len(used_nodes)
                delta_egress = sum(G.get(u, {}).get(v, {}).get('cost', 0) for u, v in best_path_edges)
                current_egress += delta_egress
                affected_out = set()
                affected_in = set()
                for u, v in best_path_edges:
                    flow[(u, v)] += 1
                    if flow[(u, v)] == 1:
                        used_out.setdefault(u, set()).add(v)
                        affected_out.add(u)
                        used_in.setdefault(v, set()).add(u)
                        affected_in.add(v)
                checked = set(best_path_edges)
                for u in affected_out:
                    for vv in used_out[u]:
                        checked.add((u, vv))
                for v in affected_in:
                    for uu in used_in[v]:
                        checked.add((uu, v))
                max_checked_load = 0.0
                for e in checked:
                    uu, vv = e
                    new_fl = flow[e]
                    new_k_u = len(used_out.get(uu, set()))
                    cap_eg = get_egress(uu) / new_k_u if new_k_u > 0 else float('inf')
                    new_m_v = len(used_in.get(vv, set()))
                    cap_in = get_ingress(vv) / new_m_v if new_m_v > 0 else float('inf')
                    thru = G.get(uu, {}).get(vv, {}).get('throughput', float('inf'))
                    new_f = min(thru, cap_eg, cap_in)
                    new_load = new_fl / new_f if new_f > 0 else float('inf')
                    max_checked_load = max(max_checked_load, new_load)
                current_max_load = max(current_max_load, max_checked_load)
                path_list = [[u, v, G.get(u, {}).get(v, {})] for u, v in best_path_edges]
                bc.set_dst_partition_paths(dst, pid, path_list)
    return bc
"""
        return {"code": code}