import os
import json
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import networkx as nx
from collections import defaultdict

# Heuristic broadcast topology optimizer balancing cost and predicted transfer time.
# It splits partitions across near-cheapest paths while estimating throughput sharing
# under node ingress/egress limits and edge capacities.


class BroadCastTopology:
    def __init__(self, src: str, dsts: list, num_partitions: int):
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

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list):
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        self.num_partitions = num_partitions


def search_algorithm(src, dsts, G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Design routing paths for broadcasting data partitions to multiple destinations.
    Heuristic approach:
      - For each destination, compute K cost-based shortest simple paths.
      - Assign partitions in round-robin across destinations, selecting for each
        partition the path that stays within a near-cheapest cost band but minimizes
        predicted makespan under simple throughput sharing model.

    Returns:
        BroadCastTopology object
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Constants and configuration for heuristic
    K_CANDIDATES = 6
    COST_REL_TOL = 0.10   # allow 10% above cheapest path
    COST_ABS_TOL = 0.01   # allow small absolute difference
    TIME_REL_SLACK = 0.05 # if cheapest path increases predicted time less than 5% vs best, pick cheapest

    # Provider limits (Gbps) per region (per provider), multiplied by num_vms
    # Defaults per problem statement
    provider_ingress = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
    provider_egress = {"aws": 5.0,  "gcp": 7.0,  "azure": 16.0}
    # Use default VM count = 2 as per specification; search_algorithm does not receive num_vms directly
    num_vms = 2
    provider_ingress = {k: v * num_vms for k, v in provider_ingress.items()}
    provider_egress = {k: v * num_vms for k, v in provider_egress.items()}

    def get_provider(node: str) -> str:
        if not isinstance(node, str):
            return "aws"
        parts = node.split(":", 1)
        if len(parts) >= 1 and parts[0]:
            prov = parts[0].strip().lower()
            if prov in provider_ingress:
                return prov
        # fallback if unknown prefix
        return "aws"

    # Cache provider lookup
    provider_cache = {}

    def prov(node):
        if node in provider_cache:
            return provider_cache[node]
        p = get_provider(node)
        provider_cache[node] = p
        return p

    # Precompute candidate paths by cost for each destination
    candidates_by_dst = {}
    for dst in dsts:
        candidates_by_dst[dst] = _k_shortest_paths_cost(G, src, dst, K_CANDIDATES)

    # State for predicted throughput sharing model
    # edge_counts[(u,v)] = number of partitions routed over this edge
    edge_counts = defaultdict(int)
    # number of distinct used outgoing/incoming edges per node (only count edges with >0 partitions)
    used_out_edge_count = defaultdict(int)
    used_in_edge_count = defaultdict(int)

    # for speed: set of edges currently used at least once
    used_edges = set()

    # main assignment loop: round-robin over partitions and destinations
    for part in range(num_partitions):
        for dst in dsts:
            # ensure there is at least one candidate path
            cand_paths = candidates_by_dst.get(dst, [])
            if not cand_paths:
                # fallback: single dijkstra path by cost
                path_nodes = _single_path_by_cost(G, src, dst)
                if path_nodes is None:
                    # As ultimate fallback, try unweighted shortest path
                    try:
                        path_nodes = nx.shortest_path(G, src, dst)
                    except Exception:
                        path_nodes = None
                if path_nodes is None:
                    # If still cannot find a path, skip (should not happen in provided configs)
                    bc_topology.set_dst_partition_paths(dst, part, [])
                    continue
                cand_paths = [path_nodes]
                candidates_by_dst[dst] = cand_paths  # cache minimal

            # Evaluate predicted time and cost for candidates
            path_infos = []
            min_cost = None
            for nodes_path in cand_paths:
                edges_list = _nodes_to_edges(G, nodes_path)
                path_cost = _path_cost(G, nodes_path)
                if min_cost is None or path_cost < min_cost:
                    min_cost = path_cost
                t_pred = _predict_makespan_after_add(
                    G,
                    edges_list,
                    edge_counts,
                    used_out_edge_count,
                    used_in_edge_count,
                    used_edges,
                    provider_ingress,
                    provider_egress,
                    prov
                )
                path_infos.append((nodes_path, edges_list, path_cost, t_pred))

            # Candidate selection with cost band and time optimization
            acceptable = []
            cheap_threshold = (min_cost if min_cost is not None else 0.0) * (1.0 + COST_REL_TOL) + COST_ABS_TOL
            for nodes_path, edges_list, path_cost, t_pred in path_infos:
                if path_cost <= cheap_threshold:
                    acceptable.append((nodes_path, edges_list, path_cost, t_pred))

            if not acceptable:
                acceptable = path_infos

            # Choose minimum predicted time among acceptable
            best_t = None
            best_by_time = None
            for info in acceptable:
                t_pred = info[3]
                if best_t is None or t_pred < best_t:
                    best_t = t_pred
                    best_by_time = info

            # Also compute cheapest candidate (global min by cost)
            cheapest = None
            cheapest_cost = None
            cheapest_t = None
            for info in path_infos:
                pc = info[2]
                if cheapest is None or pc < cheapest_cost:
                    cheapest = info
                    cheapest_cost = pc
                    cheapest_t = info[3]

            # Decision: if cheapest's predicted time is within TIME_REL_SLACK of best-by-time, pick cheapest
            chosen = None
            if cheapest_t is not None and best_t is not None:
                if cheapest_t <= best_t * (1.0 + TIME_REL_SLACK):
                    chosen = cheapest
                else:
                    chosen = best_by_time
            else:
                # Fallback
                chosen = best_by_time if best_by_time is not None else cheapest if cheapest is not None else path_infos[0]

            chosen_nodes_path, chosen_edges_list, chosen_cost, chosen_t = chosen

            # Update state with chosen path
            _apply_path_update_counts(
                chosen_edges_list,
                edge_counts,
                used_out_edge_count,
                used_in_edge_count,
                used_edges
            )

            # Assign path to topology
            bc_edges = []
            for (u, v) in chosen_edges_list:
                bc_edges.append([u, v, G[u][v]])
            bc_topology.set_dst_partition_paths(dst, part, bc_edges)

    return bc_topology


def _k_shortest_paths_cost(G: nx.DiGraph, src: str, dst: str, k: int):
    """Return up to k shortest simple paths by 'cost' edge attribute."""
    paths = []
    try:
        gen = nx.shortest_simple_paths(G, src, dst, weight=lambda u, v, d: d.get("cost", 0.0))
        for i, p in enumerate(gen):
            paths.append(p)
            if len(paths) >= k:
                break
    except Exception:
        # Fallback to single path by cost
        p = _single_path_by_cost(G, src, dst)
        if p is not None:
            paths.append(p)
    return paths


def _single_path_by_cost(G: nx.DiGraph, src: str, dst: str):
    try:
        return nx.dijkstra_path(G, src, dst, weight=lambda u, v, d: d.get("cost", 0.0))
    except Exception:
        return None


def _nodes_to_edges(G: nx.DiGraph, nodes_path):
    edges = []
    for i in range(len(nodes_path) - 1):
        u = nodes_path[i]
        v = nodes_path[i + 1]
        if not G.has_edge(u, v):
            # If for any reason edge missing, skip; handled later
            continue
        edges.append((u, v))
    return edges


def _path_cost(G: nx.DiGraph, nodes_path):
    c = 0.0
    for i in range(len(nodes_path) - 1):
        u = nodes_path[i]
        v = nodes_path[i + 1]
        data = G[u][v]
        c += float(data.get("cost", 0.0))
    return c


def _predict_makespan_after_add(
    G: nx.DiGraph,
    path_edges,
    edge_counts,
    used_out_edge_count,
    used_in_edge_count,
    used_edges_set,
    provider_ingress,
    provider_egress,
    prov_fn
):
    """
    Predicts the max per-edge time measure (|P_e| / eff_e) after adding one partition along path_edges.
    eff_e = min(edge_throughput, egress_limit(provider(u))/n_out_used(u), ingress_limit(provider(v))/n_in_used(v))
    """
    # Copies of counts to simulate after addition
    new_edge_counts = edge_counts.copy()
    new_used_out = used_out_edge_count.copy()
    new_used_in = used_in_edge_count.copy()
    new_used_edges = set(used_edges_set)

    # Apply the path: increment counts; if it's a new edge, increment node used edge counters
    for (u, v) in path_edges:
        was_used = (new_edge_counts[(u, v)] > 0)
        new_edge_counts[(u, v)] += 1
        new_used_edges.add((u, v))
        if not was_used:
            new_used_out[u] += 1
            new_used_in[v] += 1

    # Compute per-edge effective throughput and time metric
    tmax = 0.0
    for (u, v) in new_used_edges:
        cnt = new_edge_counts[(u, v)]
        if cnt <= 0:
            continue
        data = G[u][v]
        edge_thr = float(data.get("throughput", 1.0))
        # Node shares
        u_prov = prov_fn(u)
        v_prov = prov_fn(v)
        egr_lim = provider_egress.get(u_prov, 10.0)
        ing_lim = provider_ingress.get(v_prov, 10.0)
        n_out = max(1, new_used_out[u])
        n_in = max(1, new_used_in[v])
        share_egr = egr_lim / n_out
        share_ing = ing_lim / n_in
        eff = min(edge_thr, share_egr, share_ing)
        if eff <= 0:
            # Avoid division by zero; penalize heavily
            eff = 1e-9
        t = cnt / eff
        if t > tmax:
            tmax = t
    return tmax


def _apply_path_update_counts(
    path_edges,
    edge_counts,
    used_out_edge_count,
    used_in_edge_count,
    used_edges_set
):
    """
    Apply the chosen path to the global counters (mutates dicts in-place).
    """
    for (u, v) in path_edges:
        if edge_counts[(u, v)] == 0:
            used_out_edge_count[u] += 1
            used_in_edge_count[v] += 1
            used_edges_set.add((u, v))
        edge_counts[(u, v)] += 1
'''
        return {"code": code}
