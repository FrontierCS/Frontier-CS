import json
import os
import random
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import networkx as nx
import random
import math
from collections import defaultdict

def _provider_of(node: str) -> str:
    if not isinstance(node, str):
        return ""
    if ":" in node:
        return node.split(":", 1)[0].strip().lower()
    return ""

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
    # Defensive checks
    if not isinstance(num_partitions, int) or num_partitions <= 0:
        num_partitions = 1
    if src not in G.nodes:
        # If src is not in graph, we cannot proceed; create empty topology
        return BroadCastTopology(src, dsts, num_partitions)

    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Compute edge stats
    all_edges = list(G.edges(data=True))
    if not all_edges:
        # no edges -> cannot route
        return bc_topology

    # Default throughput if missing or non-positive
    # Use a robust median-like default based on observed throughputs
    thr_values = []
    cost_values = []
    for _, _, data in all_edges:
        t = data.get("throughput", None)
        if isinstance(t, (int, float)) and t > 0:
            thr_values.append(float(t))
        c = data.get("cost", None)
        if isinstance(c, (int, float)) and c >= 0:
            cost_values.append(float(c))
    default_thr = 10.0
    if thr_values:
        thr_values_sorted = sorted(thr_values)
        m_idx = len(thr_values_sorted) // 2
        default_thr = thr_values_sorted[m_idx]
        if default_thr <= 0:
            default_thr = max(1.0, sum(thr_values_sorted)/len(thr_values_sorted))
    if not cost_values:
        cost_min, cost_max = 0.0, 1.0
    else:
        cost_min = min(cost_values)
        cost_max = max(cost_values)
        if cost_max == cost_min:
            cost_max = cost_min + 1.0
    cost_range = max(cost_max - cost_min, 1e-9)

    # Build candidate trees with different weighting
    # Edge weight function: w = cost_coef * cost + alpha * (1/throughput) + cross_penalty * is_cross_provider + eps
    # Generate parameter sets to diversify candidates
    def make_weight_func(alpha: float, cost_coef: float, cross_penalty: float, jitter: float):
        def weight(u, v, data):
            c = data.get("cost", 0.0)
            if not isinstance(c, (int, float)):
                try:
                    c = float(c)
                except:
                    c = 0.0
            t = data.get("throughput", default_thr)
            if not isinstance(t, (int, float)) or t <= 0:
                t = default_thr
            inv_t = 1.0 / max(t, 1e-12)
            cross = 1.0 if _provider_of(u) != _provider_of(v) else 0.0
            # small jitter to break ties
            j = (random.random() * jitter) if jitter > 0 else 0.0
            return cost_coef * c + alpha * inv_t + cross_penalty * cross + j
        return weight

    # Base parameter sets
    # Scale alpha relative to cost_range to make inverse-throughput term comparable
    alpha_small = 0.05 * cost_range
    alpha_med = 0.15 * cost_range
    alpha_big = 0.30 * cost_range
    cross_pen_small = 0.02 * cost_range
    cross_pen_med = 0.05 * cost_range

    param_sets = [
        # prioritize cost
        (0.0, 1.0, 0.0, 1e-7),
        # cost + light throughput sensitivity
        (alpha_small, 1.0, 0.0, 1e-7),
        # cost + cross penalty
        (alpha_small, 1.0, cross_pen_small, 1e-7),
        # balanced
        (alpha_med, 1.0, cross_pen_small, 1e-7),
        # more throughput-aware
        (alpha_big, 0.9, cross_pen_med, 1e-7),
        # slightly cheaper cost coefficient to diversify
        (alpha_med, 0.8, cross_pen_small, 1e-7),
    ]

    num_trees = min(max(3, min(6, num_partitions)), len(param_sets))

    # Build candidate trees: as union of shortest paths (by SSSP) from src to each dst under given weight
    candidates = []
    for i in range(num_trees):
        alpha, cost_coef, cross_pen, jitter = param_sets[i]
        weight_fn = make_weight_func(alpha, cost_coef, cross_pen, jitter)

        # Single-source dijkstra for all nodes
        try:
            lengths, paths = nx.single_source_dijkstra(G, source=src, weight=weight_fn)
        except Exception:
            # Fallback: we will compute per-dst
            lengths, paths = {}, {}

        cand_paths_map = {}
        cand_edges_set = set()
        path_missing = False

        for d in dsts:
            path_nodes = paths.get(d, None)
            if path_nodes is None:
                # Fallback per-dst search
                try:
                    path_nodes = nx.dijkstra_path(G, src, d, weight=weight_fn)
                except Exception:
                    try:
                        path_nodes = nx.shortest_path(G, src, d)  # unweighted fallback
                    except Exception:
                        path_nodes = None
            if path_nodes is None or len(path_nodes) < 2:
                path_missing = True
                break

            cand_paths_map[d] = path_nodes
            for a, b in zip(path_nodes[:-1], path_nodes[1:]):
                # avoid self-loops
                if a == b:
                    continue
                cand_edges_set.add((a, b))

        if path_missing or not cand_edges_set:
            # If this candidate is invalid, skip
            continue

        # Incremental cost (per partition) of using this tree: sum of unique edge costs
        inc_cost = 0.0
        for (u, v) in cand_edges_set:
            data = G[u][v]
            c = data.get("cost", 0.0)
            if isinstance(c, (int, float)):
                inc_cost += float(c)
            else:
                try:
                    inc_cost += float(c)
                except:
                    inc_cost += 0.0

        candidates.append({
            "paths_map": cand_paths_map,   # dst -> list of nodes
            "edges_set": cand_edges_set,   # set of (u, v)
            "inc_cost": inc_cost,
            "num_edges": len(cand_edges_set),
            "alpha": alpha,
            "cost_coef": cost_coef,
            "cross_pen": cross_pen
        })

    # Ensure at least one candidate; if none, build trivial per-destination cheapest (by cost only)
    if not candidates:
        weight_fn = make_weight_func(0.0, 1.0, 0.0, 1e-7)
        cand_paths_map = {}
        cand_edges_set = set()
        for d in dsts:
            try:
                path_nodes = nx.dijkstra_path(G, src, d, weight=weight_fn)
            except Exception:
                try:
                    path_nodes = nx.shortest_path(G, src, d)
                except Exception:
                    # give up for this dst; use any 2-hop if exists
                    path_nodes = None
                    # Try to connect via any neighbor of src
                    for nbr in G.successors(src):
                        try:
                            tail = nx.dijkstra_path(G, nbr, d, weight=weight_fn)
                            path_nodes = [src] + tail
                            break
                        except Exception:
                            continue
            if path_nodes is None or len(path_nodes) < 2:
                # still not found, skip this dst
                path_nodes = [src]
                if src != d and G.has_edge(src, d):
                    path_nodes.append(d)
                elif src == d:
                    pass
                else:
                    # cannot do anything
                    pass
            cand_paths_map[d] = path_nodes
            for a, b in zip(path_nodes[:-1], path_nodes[1:]):
                if a == b:
                    continue
                cand_edges_set.add((a, b))

        inc_cost = 0.0
        for (u, v) in cand_edges_set:
            data = G[u][v]
            c = data.get("cost", 0.0)
            try:
                inc_cost += float(c)
            except:
                inc_cost += 0.0

        candidates.append({
            "paths_map": cand_paths_map,
            "edges_set": cand_edges_set,
            "inc_cost": inc_cost,
            "num_edges": len(cand_edges_set),
            "alpha": 0.0,
            "cost_coef": 1.0,
            "cross_pen": 0.0
        })

    # Greedy assignment of partitions to candidate trees to balance throughput proxy and minimize incremental cost
    # P_e counts number of partitions using edge e (unique by partition id)
    P_e = defaultdict(int)
    # Precompute per-edge throughput
    edge_thr = {}
    for (u, v, data) in all_edges:
        t = data.get("throughput", default_thr)
        if not isinstance(t, (int, float)) or t <= 0:
            t = default_thr
        edge_thr[(u, v)] = float(t)

    # Current max time proxy over edges: max_e P_e / throughput_e (partition count per Gbps)
    current_max_time = 0.0

    # Precompute path edges for each candidate per destination, to avoid recomputing later
    # Also build edge lists for bc_topology later
    def build_edge_list_from_nodes(path_nodes):
        edges = []
        for u, v in zip(path_nodes[:-1], path_nodes[1:]):
            if u == v:
                continue
            # Guarantee edge exists; if not, skip
            if not G.has_edge(u, v):
                # try reversed not appropriate
                continue
            edges.append([u, v, G[u][v]])
        return edges

    # Build per-candidate per-destination edge-lists
    for cand in candidates:
        per_dst_edges = {}
        for d in dsts:
            nodes = cand["paths_map"].get(d, None)
            if nodes is None:
                per_dst_edges[d] = []
            else:
                per_dst_edges[d] = build_edge_list_from_nodes(nodes)
        cand["per_dst_edges"] = per_dst_edges

    # Assignment loop
    # Choose tree for each partition to minimize max time proxy, then by incremental cost, then by number of edges
    assignment = []  # list of candidate index per partition
    for p in range(num_partitions):
        best_idx = 0
        best_tuple = (float("inf"), float("inf"), float("inf"))  # (new_max_time, inc_cost, num_edges)
        for idx, cand in enumerate(candidates):
            edges_set = cand["edges_set"]
            # Compute new max time proxy if assigning this partition to this tree
            local_max = current_max_time
            for e in edges_set:
                thr = edge_thr.get(e, default_thr)
                new_pcount = P_e[e] + 1
                ratio = new_pcount / max(thr, 1e-12)
                if ratio > local_max:
                    local_max = ratio
            obj_tuple = (local_max, cand["inc_cost"], cand["num_edges"])
            if obj_tuple < best_tuple:
                best_tuple = obj_tuple
                best_idx = idx

        # Assign partition p to best candidate tree
        chosen = candidates[best_idx]
        assignment.append(best_idx)
        for e in chosen["edges_set"]:
            P_e[e] += 1
        # Update current max time proxy
        current_max_time = best_tuple[0]

    # Finally, populate bc_topology paths per (dst, partition) according to assignment
    for p, idx in enumerate(assignment):
        cand = candidates[idx]
        for d in dsts:
            path_nodes = cand["paths_map"].get(d)
            if path_nodes is None or len(path_nodes) < 2:
                # Attempt basic path with cost-only weight
                try:
                    path_nodes = nx.dijkstra_path(G, src, d, weight=lambda u, v, data: float(data.get("cost", 0.0)))
                except Exception:
                    try:
                        path_nodes = nx.shortest_path(G, src, d)
                    except Exception:
                        path_nodes = [src, d] if G.has_edge(src, d) else [src]
            # Build edges list and set
            edge_list = []
            for u, v in zip(path_nodes[:-1], path_nodes[1:]):
                if u == v:
                    continue
                if not G.has_edge(u, v):
                    # skip missing
                    continue
                edge_list.append([u, v, G[u][v]])
            bc_topology.set_dst_partition_paths(d, p, edge_list)

    # Ensure all partitions have paths for all dsts, fill any missing with cost-only shortest paths
    for d in dsts:
        for p in range(num_partitions):
            plist = bc_topology.paths.get(d, {}).get(str(p))
            if plist is None or not isinstance(plist, list) or len(plist) == 0:
                try:
                    path_nodes = nx.dijkstra_path(G, src, d, weight=lambda u, v, data: float(data.get("cost", 0.0)))
                except Exception:
                    try:
                        path_nodes = nx.shortest_path(G, src, d)
                    except Exception:
                        path_nodes = [src, d] if G.has_edge(src, d) else [src]
                edge_list = []
                for u, v in zip(path_nodes[:-1], path_nodes[1:]):
                    if u == v:
                        continue
                    if not G.has_edge(u, v):
                        continue
                    edge_list.append([u, v, G[u][v]])
                bc_topology.set_dst_partition_paths(d, p, edge_list)

    return bc_topology
'''
        return {"code": code}