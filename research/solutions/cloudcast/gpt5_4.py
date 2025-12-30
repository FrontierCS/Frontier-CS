import json
import os
import random
import math
import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import random
import networkx as nx

# Helper constants for bandwidth limits (Gbps) per region per provider
DEFAULT_NUM_VMS = 2
INGRESS_PER_VM = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
EGRESS_PER_VM = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}


def _get_provider(node: str) -> str:
    if not isinstance(node, str):
        return "aws"
    parts = node.split(":", 1)
    if len(parts) == 0:
        return "aws"
    provider = parts[0].lower()
    if provider in ("aws", "gcp", "azure"):
        return provider
    return "aws"


def _ingress_limit(node: str, num_vms: int = DEFAULT_NUM_VMS) -> float:
    prov = _get_provider(node)
    base = INGRESS_PER_VM.get(prov, 10.0)
    return base * float(num_vms)


def _egress_limit(node: str, num_vms: int = DEFAULT_NUM_VMS) -> float:
    prov = _get_provider(node)
    base = EGRESS_PER_VM.get(prov, 5.0)
    return base * float(num_vms)


def _edge_cost(G: nx.DiGraph, u, v):
    d = G[u][v]
    return float(d.get("cost", 0.0))


def _edge_throughput(G: nx.DiGraph, u, v):
    d = G[u][v]
    thr = d.get("throughput", None)
    if thr is None:
        return 1e9  # effectively infinite if not specified
    try:
        return float(thr)
    except Exception:
        return 1e9


def _path_edges_from_nodes(path_nodes):
    edges = []
    for i in range(len(path_nodes) - 1):
        edges.append((path_nodes[i], path_nodes[i + 1]))
    return edges


def _path_cost(G: nx.DiGraph, nodes_path):
    total = 0.0
    for i in range(len(nodes_path) - 1):
        u, v = nodes_path[i], nodes_path[i + 1]
        total += _edge_cost(G, u, v)
    return total


def _k_shortest_paths_by_cost(G: nx.DiGraph, src, dst, k: int = 5):
    paths = []
    try:
        gen = nx.shortest_simple_paths(G, src, dst, weight="cost")
        for idx, p in enumerate(gen):
            paths.append(p)
            if len(paths) >= k:
                break
    except Exception:
        try:
            p = nx.dijkstra_path(G, src, dst, weight="cost")
            paths.append(p)
        except Exception:
            try:
                p = nx.shortest_path(G, src, dst)
                paths.append(p)
            except Exception:
                return []
    return paths


def _throughput_weighted_path(G: nx.DiGraph, src, dst, alpha: float = 0.05):
    # Find a path minimizing: sum(cost + alpha/throughput)
    def w(u, v, d):
        thr = d.get("throughput", None)
        thr = float(thr) if thr is not None else 1e9
        return float(d.get("cost", 0.0)) + alpha / max(thr, 1e-9)
    try:
        return nx.dijkstra_path(G, src, dst, weight=w)
    except Exception:
        return []


def _dedup_paths(paths):
    seen = set()
    uniq = []
    for p in paths:
        t = tuple(p)
        if t not in seen:
            seen.add(t)
            uniq.append(p)
    return uniq


def _compute_global_T(G: nx.DiGraph, loads, used_out_edges, used_in_edges, num_vms: int = DEFAULT_NUM_VMS):
    # T = max_over_used_edges(load / f_e)
    T = 0.0
    tiny = 1e-9
    for (u, v), load in loads.items():
        if load <= 0:
            continue
        edge_thr = _edge_throughput(G, u, v)
        out_deg = len(used_out_edges.get(u, ()))
        in_deg = len(used_in_edges.get(v, ()))
        egress_share = _egress_limit(u, num_vms=num_vms) / max(1, out_deg)
        ingress_share = _ingress_limit(v, num_vms=num_vms) / max(1, in_deg)
        f_e = min(edge_thr, egress_share, ingress_share)
        T = max(T, float(load) / max(f_e, tiny))
    return T


def _evaluate_candidate_T_after(G: nx.DiGraph, path_nodes, used_edges, loads, used_out_edges, used_in_edges, T_current, num_vms: int = DEFAULT_NUM_VMS):
    # Approximate T_after considering:
    # - load increases on edges in the candidate path
    # - degree increases on nodes where we add new unique out/in edges
    # - recompute times for edges affected by those deg changes
    if not path_nodes or len(path_nodes) == 1:
        return T_current

    path_edges = _path_edges_from_nodes(path_nodes)
    path_edge_set = set(path_edges)

    new_edges = set()
    affected_out_nodes = set()
    affected_in_nodes = set()

    # Determine new unique edges added by this path
    for (u, v) in path_edges:
        if (u, v) not in used_edges:
            new_edges.add((u, v))
            affected_out_nodes.add(u)
            affected_in_nodes.add(v)

    # Collect affected existing edges (due to degree increase)
    affected_used_edges = set()
    for u in affected_out_nodes:
        for v2 in used_out_edges.get(u, ()):
            affected_used_edges.add((u, v2))
    for v in affected_in_nodes:
        for u2 in used_in_edges.get(v, ()):
            affected_used_edges.add((u2, v))

    # Add path edges themselves (existing or new) for recomputation (load change)
    affected_used_edges.update([e for e in path_edges if e in used_edges])

    # We'll compute predicted times on:
    #  - all 'affected_used_edges' with updated deg (if applicable) and updated load (if in path)
    #  - all 'new_edges' (load=1)
    tiny = 1e-9
    local_max = 0.0

    # Precompute predicted degrees for affected nodes
    pred_out_deg = {}
    pred_in_deg = {}

    for u in affected_out_nodes:
        pred_out_deg[u] = len(used_out_edges.get(u, ())) + 1
    for v in affected_in_nodes:
        pred_in_deg[v] = len(used_in_edges.get(v, ())) + 1

    def get_pred_out_deg(u):
        if u in pred_out_deg:
            return pred_out_deg[u]
        return len(used_out_edges.get(u, ()))

    def get_pred_in_deg(v):
        if v in pred_in_deg:
            return pred_in_deg[v]
        return len(used_in_edges.get(v, ()))

    # Existing used edges affected by deg increases or path load additions
    for (u, v) in affected_used_edges:
        edge_thr = _edge_throughput(G, u, v)
        egress_share = _egress_limit(u, num_vms=num_vms) / max(1, get_pred_out_deg(u))
        ingress_share = _ingress_limit(v, num_vms=num_vms) / max(1, get_pred_in_deg(v))
        f_e = min(edge_thr, egress_share, ingress_share)
        load = loads.get((u, v), 0)
        if (u, v) in path_edge_set:
            load += 1
        local_max = max(local_max, float(load) / max(f_e, tiny))

    # New edges added
    for (u, v) in new_edges:
        edge_thr = _edge_throughput(G, u, v)
        egress_share = _egress_limit(u, num_vms=num_vms) / max(1, get_pred_out_deg(u))
        ingress_share = _ingress_limit(v, num_vms=num_vms) / max(1, get_pred_in_deg(v))
        f_e = min(edge_thr, egress_share, ingress_share)
        load = 1  # first partition on this edge
        local_max = max(local_max, float(load) / max(f_e, tiny))

    # T_after is the max of current T and any changed edges
    return max(T_current, local_max)


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> 'BroadCastTopology':
    # Initialize broadcast topology
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Handle trivial case
    if num_partitions <= 0:
        bc_topology.set_num_partitions(0)
        return bc_topology

    # Prepare candidate paths per destination
    K_COST = 5
    ALPHA_THR = 0.05  # throughput penalty factor for alternative path
    candidates = {}

    for dst in dsts:
        if dst == src:
            candidates[dst] = [[src]]
            continue
        cost_paths = _k_shortest_paths_by_cost(G, src, dst, k=K_COST)
        thr_path = _throughput_weighted_path(G, src, dst, alpha=ALPHA_THR)
        comb = []
        comb.extend(cost_paths)
        if thr_path:
            comb.append(thr_path)
        comb = _dedup_paths(comb)
        if not comb:
            # Fallback to any path (ensure at least one)
            try:
                p = nx.shortest_path(G, src, dst)
                comb = [p]
            except Exception:
                comb = []
        candidates[dst] = comb

    # Global structures for load and degree counting
    used_edges = set()                # set of (u, v)
    loads = {}                        # (u, v) -> number of partitions using it
    used_out_edges = {}               # u -> set of v
    used_in_edges = {}                # v -> set of u

    # Current approximate max time metric (load/f_e)
    T_current = 0.0

    # Determine ordering of destination processing to spread decision impact
    dsts_order = list(dsts)
    random.shuffle(dsts_order)

    # Assign paths partition-by-partition in rounds to balance load
    COST_TOL_REL = 0.10  # allow up to +10% cost for better time

    for p in range(num_partitions):
        # randomize per-round order for fairness
        random.shuffle(dsts_order)
        for dst in dsts_order:
            if dst == src:
                # source equals destination: empty path
                bc_topology.set_dst_partition_paths(dst, p, [])
                continue

            cand_paths = candidates.get(dst, [])
            if not cand_paths:
                # Attempt to find at least one path now
                try:
                    path_nodes = nx.dijkstra_path(G, src, dst, weight="cost")
                except Exception:
                    try:
                        path_nodes = nx.shortest_path(G, src, dst)
                    except Exception:
                        path_nodes = [src, dst] if G.has_edge(src, dst) else [src]
                cand_paths = [path_nodes]

            # Compute costs for candidates
            cand_infos = []
            min_cost = None
            for path_nodes in cand_paths:
                c = _path_cost(G, path_nodes)
                if min_cost is None or c < min_cost:
                    min_cost = c
                cand_infos.append((path_nodes, c))

            # Filter by cost tolerance
            allowed = []
            tol = (min_cost if min_cost is not None else 0.0) * (1.0 + COST_TOL_REL)
            for path_nodes, c in cand_infos:
                if c <= tol:
                    allowed.append((path_nodes, c))
            if not allowed:
                allowed = cand_infos

            # Choose candidate that minimizes T_after among allowed; tiebreaker: cost then path length
            best = None
            best_T_after = None
            for path_nodes, c in allowed:
                T_after = _evaluate_candidate_T_after(G, path_nodes, used_edges, loads, used_out_edges, used_in_edges, T_current, num_vms=DEFAULT_NUM_VMS)
                score_tuple = (T_after, c, len(path_nodes))
                if best is None or score_tuple < best:
                    best = score_tuple
                    best_choice = (path_nodes, c)

            chosen_path_nodes, chosen_cost = best_choice

            # Commit chosen path: update loads, used edges, degrees
            path_edges = _path_edges_from_nodes(chosen_path_nodes)
            for (u, v) in path_edges:
                if (u, v) not in used_edges:
                    used_edges.add((u, v))
                    used_out_edges.setdefault(u, set()).add(v)
                    used_in_edges.setdefault(v, set()).add(u)
                loads[(u, v)] = loads.get((u, v), 0) + 1

            # Recompute exact T_current to keep accurate
            T_current = _compute_global_T(G, loads, used_out_edges, used_in_edges, num_vms=DEFAULT_NUM_VMS)

            # Store path into topology
            edge_list = []
            for (u, v) in path_edges:
                edge_list.append([u, v, G[u][v]])
            bc_topology.set_dst_partition_paths(dst, p, edge_list)

    return bc_topology


class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
        # Each edge is [src_node, dst_node, edge_data_dict]
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
'''
        return {"code": code}