import json
import os

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import networkx as nx

def _path_cost(G, path):
    total = 0.0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        data = G[u][v]
        total += float(data.get("cost", 0.0))
    return total

def _path_bottleneck_throughput(G, path):
    if len(path) <= 1:
        return float("inf")
    b = float("inf")
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        thr = float(G[u][v].get("throughput", 0.0))
        if thr < b:
            b = thr
    return b

def _unique_paths(paths):
    seen = set()
    out = []
    for p in paths:
        t = tuple(p)
        if t not in seen:
            seen.add(t)
            out.append(p)
    return out

def _k_shortest_paths_by_cost(G, src, dst, k=8):
    paths = []
    try:
        gen = nx.shortest_simple_paths(G, src, dst, weight="cost")
        for _, p in zip(range(k * 2), gen):  # fetch a few extra in case of duplicates
            paths.append(p)
    except Exception:
        try:
            p = nx.dijkstra_path(G, src, dst, weight="cost")
            paths = [p]
        except Exception:
            try:
                p = nx.shortest_path(G, src, dst)
                paths = [p]
            except Exception:
                paths = []
    paths = _unique_paths(paths)
    # sort strictly by cost
    paths.sort(key=lambda p: _path_cost(G, p))
    # keep top k
    return paths[:k]

def _select_paths_for_destination(G, src, dst, num_partitions, cost_tol=0.08, low_thr_threshold=3.0, max_paths_split=3):
    cand_paths = _k_shortest_paths_by_cost(G, src, dst, k=max(4, min(10, num_partitions * 2 if num_partitions < 5 else 8)))
    if not cand_paths:
        return [], []
    costs = [ _path_cost(G, p) for p in cand_paths ]
    bottlenecks = [ _path_bottleneck_throughput(G, p) for p in cand_paths ]
    base_cost = costs[0]
    # consider near-optimal set within tolerance
    near_paths = []
    for p, c, b in zip(cand_paths, costs, bottlenecks):
        if c <= base_cost * (1.0 + cost_tol):
            near_paths.append((p, c, b))
    if not near_paths:
        near_paths = [(cand_paths[0], costs[0], bottlenecks[0])]

    # choose primary path: within near set, maximize bottleneck throughput, tie-break by cost, then shorter hops
    near_paths.sort(key=lambda pcb: (-pcb[2], pcb[1], len(pcb[0])))
    primary = near_paths[0]
    selected = [primary]
    # decide if we want to split across multiple paths
    # split only if primary bottleneck is low and there exist other near-optimal with significantly better throughput
    others = near_paths[1:]
    improved_others = [pcb for pcb in others if pcb[2] >= max(low_thr_threshold, primary[2] * 1.25)]
    # keep up to max_paths_split - 1 more, sorted by throughput desc then cost asc
    improved_others.sort(key=lambda pcb: (-pcb[2], pcb[1], len(pcb[0])))
    if improved_others and num_partitions >= 2:
        extra = improved_others[:max_paths_split - 1]
        selected.extend(extra)

    # determine partition counts per selected path
    sel_bottlenecks = [max(1e-9, s[2]) for s in selected]
    total_thr = sum(sel_bottlenecks)
    counts = []
    if len(selected) == 1:
        counts = [num_partitions]
    else:
        # proportional allocation by bottleneck throughput
        raw = [ (s_thr / total_thr) * num_partitions for s_thr in sel_bottlenecks ]
        floor = [int(x) for x in raw]
        remainder = num_partitions - sum(floor)
        # distribute remainder by largest fractional part
        fracs = [ (raw[i] - floor[i], i) for i in range(len(raw)) ]
        fracs.sort(reverse=True)
        counts = floor[:]
        for j in range(remainder):
            counts[fracs[j % len(fracs)][1]] += 1
        # ensure no zero if possible
        # if some path got zero and num_partitions >= len(selected), make at least 1
        zeros = [i for i, c in enumerate(counts) if c == 0]
        idx = 0
        while zeros and sum(counts) == num_partitions:
            # steal from the path with largest count
            max_i = max(range(len(counts)), key=lambda i: counts[i])
            if counts[max_i] <= 1:
                break
            z = zeros.pop(0)
            counts[max_i] -= 1
            counts[z] += 1
    paths_only = [s[0] for s in selected]
    return paths_only, counts

def _path_to_edges(G, path_nodes):
    edges = []
    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i + 1]
        edges.append([u, v, G[u][v]])
    return edges

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
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    for dst in dsts:
        try:
            sel_paths, counts = _select_paths_for_destination(G, src, dst, num_partitions)
            if not sel_paths:
                # fallback to single shortest by cost
                path_nodes = nx.dijkstra_path(G, src, dst, weight="cost")
                edges = _path_to_edges(G, path_nodes)
                for pid in range(num_partitions):
                    bc_topology.set_dst_partition_paths(dst, pid, edges)
                continue
            # build list of edges per selected path
            edges_list = [ _path_to_edges(G, p) for p in sel_paths ]
            # assign partitions
            pid = 0
            for idx, cnt in enumerate(counts):
                for _ in range(cnt):
                    if pid >= num_partitions:
                        break
                    bc_topology.set_dst_partition_paths(dst, pid, edges_list[idx])
                    pid += 1
            # if due to rounding we still have remaining partitions, fill with primary path
            primary_edges = edges_list[0]
            while pid < num_partitions:
                bc_topology.set_dst_partition_paths(dst, pid, primary_edges)
                pid += 1
        except Exception:
            # robust fallback path
            try:
                path_nodes = nx.shortest_path(G, src, dst)
                edges = _path_to_edges(G, path_nodes)
                for pid in range(num_partitions):
                    bc_topology.set_dst_partition_paths(dst, pid, edges)
            except Exception:
                # no path found; leave as None paths (should not happen)
                pass
    return bc_topology
"""
        return {"code": code}
