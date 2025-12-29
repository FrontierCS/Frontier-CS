import json
import os
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import networkx as nx
from heapq import heappush, heappop

EPS = 1e-12

class BroadCastTopology:
    def __init__(self, src: str, dsts: list, num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
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


def _edge_cost(G: nx.DiGraph, u, v):
    try:
        return float(G[u][v].get("cost", 0.0))
    except Exception:
        return 0.0

def _edge_throughput(G: nx.DiGraph, u, v):
    try:
        t = G[u][v].get("throughput", None)
        if t is None:
            return 1e9
        t = float(t)
        if t <= 0:
            return EPS
        return t
    except Exception:
        return 1e9

def _path_cost(G: nx.DiGraph, path):
    total = 0.0
    for i in range(len(path)-1):
        total += _edge_cost(G, path[i], path[i+1])
    return total

def _path_bottleneck(G: nx.DiGraph, path):
    b = float("inf")
    for i in range(len(path)-1):
        b = min(b, _edge_throughput(G, path[i], path[i+1]))
    if b == float("inf"):
        b = 1e9
    return b

def _path_avg_inv_throughput(G: nx.DiGraph, path):
    if len(path) <= 1:
        return 0.0
    s = 0.0
    m = 0
    for i in range(len(path)-1):
        t = _edge_throughput(G, path[i], path[i+1])
        s += 1.0 / max(t, EPS)
        m += 1
    if m == 0:
        return 0.0
    return s / m

def _k_shortest_by_cost(G: nx.DiGraph, s, t, K: int):
    res = []
    try:
        gen = nx.shortest_simple_paths(G, s, t, weight="cost")
        for path in gen:
            res.append(path)
            if len(res) >= K:
                break
    except Exception:
        try:
            path = nx.dijkstra_path(G, s, t, weight="cost")
            res.append(path)
        except Exception:
            try:
                path = nx.shortest_path(G, s, t)
                res.append(path)
            except Exception:
                pass
    return res

def _dijkstra_cost_plus_inv_thru(G: nx.DiGraph, s, t, alpha: float):
    def weight(u, v, data):
        c = data.get("cost", 0.0)
        th = data.get("throughput", None)
        if th is None:
            th = 1e9
        try:
            thf = float(th)
            if thf <= 0:
                thf = EPS
        except Exception:
            thf = 1e9
        try:
            cf = float(c)
        except Exception:
            cf = 0.0
        return cf + alpha * (1.0 / thf)
    try:
        return nx.dijkstra_path(G, s, t, weight=weight)
    except Exception:
        return []

def _widest_path(G: nx.DiGraph, s, t):
    # Maximize minimal throughput along path, tie-break by minimal cost
    # Priority queue by (-bottleneck, cost, node)
    best_b = {}
    best_c = {}
    parent = {}
    pq = []
    heappush(pq, (-float("inf"), 0.0, s))
    best_b[s] = float("inf")
    best_c[s] = 0.0
    parent[s] = None
    visited = set()
    while pq:
        nb, c, u = heappop(pq)
        b = -nb
        if u in visited:
            continue
        visited.add(u)
        if u == t:
            break
        for v in G.successors(u):
            th = _edge_throughput(G, u, v)
            new_b = min(b, th)
            new_c = c + _edge_cost(G, u, v)
            prev_b = best_b.get(v, -1.0)
            prev_c = best_c.get(v, float("inf"))
            update = False
            if new_b > prev_b + 1e-9:
                update = True
            elif abs(new_b - prev_b) <= 1e-9 and new_c < prev_c - 1e-12:
                update = True
            if update:
                best_b[v] = new_b
                best_c[v] = new_c
                parent[v] = u
                heappush(pq, (-new_b, new_c, v))
    if t not in parent:
        return []
    # Reconstruct path
    path = []
    cur = t
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur, None)
    path.reverse()
    # Validate directed edges exist
    for i in range(len(path)-1):
        if not G.has_edge(path[i], path[i+1]):
            return []
    return path

def _unique_paths(paths):
    seen = set()
    res = []
    for p in paths:
        tp = tuple(p)
        if tp not in seen:
            seen.add(tp)
            res.append(p)
    return res

def _select_paths_for_destination(G: nx.DiGraph, s, t, candidates, num_partitions, global_first_hop_usage):
    # Scoring parameters
    gamma = 0.05  # weight on average inverse throughput
    delta = 0.0001  # slight penalty on hop count to reduce |V|
    group_tol = 0.15  # tolerance to prefer existing first-hop
    # Determine M
    if num_partitions <= 3:
        base_M = 1
    elif num_partitions <= 7:
        base_M = 2
    else:
        base_M = 3
    # Build metrics
    metas = []
    for p in candidates:
        if len(p) < 2:
            continue
        cost = _path_cost(G, p)
        bottleneck = _path_bottleneck(G, p)
        avg_inv = _path_avg_inv_throughput(G, p)
        hops = len(p) - 1
        first_hop = None
        if len(p) >= 2:
            first_hop = p[1]
        score = cost + gamma * avg_inv + delta * hops
        metas.append({
            "path": p,
            "cost": cost,
            "bottleneck": bottleneck,
            "avg_inv": avg_inv,
            "hops": hops,
            "first_hop": first_hop,
            "score": score
        })
    if not metas:
        return []
    metas.sort(key=lambda x: (x["score"], -x["bottleneck"], x["cost"], x["hops"]))
    # Prefer existing first-hop usage if within tolerance
    best0 = metas[0]
    chosen = None
    if global_first_hop_usage:
        # Find candidate that uses most used first-hop if within tolerance
        fh_counts = global_first_hop_usage
        # Determine the best first hop by usage
        best_fh = None
        best_cnt = -1
        for fh, cnt in fh_counts.items():
            if cnt > best_cnt:
                best_cnt = cnt
                best_fh = fh
        if best_fh is not None and best_cnt > 0:
            # Find candidate with this first hop close to the best score
            for m in metas:
                if m["first_hop"] == best_fh:
                    if m["score"] <= best0["score"] * (1.0 + group_tol):
                        chosen = m
                        break
    if chosen is None:
        chosen = best0
    selected = [chosen]
    # Update global first-hop usage
    fhc = chosen["first_hop"]
    if fhc is not None:
        global_first_hop_usage[fhc] = global_first_hop_usage.get(fhc, 0) + 1
    # Decide additional paths
    M = base_M
    # If bottleneck is strong, we may reduce M to avoid extra nodes
    if chosen["bottleneck"] >= 12.0 and num_partitions <= 7:
        M = 1
    # Filter remaining
    remaining = [m for m in metas if m["path"] != chosen["path"]]
    # Preferences
    prefer_same_first_hop = (chosen["bottleneck"] >= 8.0)
    cost_tol = 0.60 if M >= 2 else 0.0
    # Try to pick additional paths respecting preferences and cost tolerance
    def acceptable(m, ref_cost):
        if m["cost"] <= ref_cost * (1.0 + cost_tol):
            return True
        # If chosen bottleneck is poor, allow a higher-cost path if it offers much better bottleneck
        if chosen["bottleneck"] < 6.0 and m["bottleneck"] > chosen["bottleneck"] * 1.5:
            return True
        return False
    ref_cost = chosen["cost"]
    # First pass: try with preference
    for m in remaining:
        if len(selected) >= M:
            break
        if acceptable(m, ref_cost):
            if prefer_same_first_hop:
                if m["first_hop"] == fhc:
                    selected.append(m)
            else:
                if m["first_hop"] != fhc:
                    selected.append(m)
    # Second pass: relax first-hop preference
    for m in remaining:
        if len(selected) >= M:
            break
        if acceptable(m, ref_cost) and m not in selected:
            selected.append(m)
    # Ensure unique paths and not exceeding M
    selected_paths = []
    seen = set()
    for m in selected:
        tp = tuple(m["path"])
        if tp not in seen:
            seen.add(tp)
            selected_paths.append(m["path"])
        if len(selected_paths) >= M:
            break
    return selected_paths

def _build_edge_list(G: nx.DiGraph, path):
    edges = []
    for i in range(len(path)-1):
        u = path[i]
        v = path[i+1]
        data = G[u][v]
        edges.append([u, v, data])
    return edges

def search_algorithm(src: str, dsts: list, G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    # Global tracking of first-hop usage out of src to reduce outgoing edge fanout
    global_first_hop_usage = {}
    # Precompute default alpha for modified Dijkstra, scale to modestly penalize low throughput edges
    alpha = 0.05
    # For each destination, generate candidate paths
    for dst in dsts:
        candidates = []
        # K shortest by cost
        K1 = max(3, min(6, max(1, num_partitions // 2)))
        cand1 = _k_shortest_by_cost(G, src, dst, K1)
        candidates.extend(cand1)
        # Modified weight path (cost + alpha / throughput)
        path_mod = _dijkstra_cost_plus_inv_thru(G, src, dst, alpha)
        if path_mod:
            candidates.append(path_mod)
        # Widest path (maximize bottleneck)
        path_wide = _widest_path(G, src, dst)
        if path_wide:
            candidates.append(path_wide)
        # Fallback: plain shortest path if none gathered
        if not candidates:
            try:
                p = nx.shortest_path(G, src, dst)
                candidates.append(p)
            except Exception:
                pass
        # Deduplicate
        candidates = _unique_paths(candidates)
        if not candidates:
            # If still no path, skip (should not happen)
            continue
        # Select up to M paths for this destination based on heuristic
        selected_paths = _select_paths_for_destination(G, src, dst, candidates, num_partitions, global_first_hop_usage)
        if not selected_paths:
            # Fallback to cheapest path
            selected_paths = [candidates[0]]
        # Assign partitions round-robin over selected paths
        m = max(1, len(selected_paths))
        for pid in range(num_partitions):
            chosen = selected_paths[pid % m]
            edges = _build_edge_list(G, chosen)
            for e in edges:
                bc_topology.append_dst_partition_path(dst, pid, e)
    return bc_topology
'''
        return {"code": code}