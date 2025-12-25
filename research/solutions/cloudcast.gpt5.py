import json
import networkx as nx
from collections import defaultdict

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

    if src not in G:
        return bc_topology

    # Parameters
    SLACK_REL = 0.20       # relative cost slack to allow alternative near-optimal paths
    SLACK_ABS = 0.02       # absolute $/GB slack to allow alternative paths
    K_BASE_MAX = max(1, min(12, num_partitions if num_partitions > 0 else 1))
    K_GEN_MAX = max(4, min(40, K_BASE_MAX * 4))
    EPS_THR = 1e-6
    NODE_ALPHA = 0.15      # small penalty for reusing nodes to avoid node-level bottlenecks

    # Precompute throughput stats for heuristics
    all_thr = []
    for _, _, d in G.edges(data=True):
        thr = d.get("throughput", 0.0)
        if thr is None:
            thr = 0.0
        all_thr.append(max(EPS_THR, float(thr)))
    if not all_thr:
        thr_median = 1.0
    else:
        sorted_thr = sorted(all_thr)
        mid = len(sorted_thr) // 2
        thr_median = sorted_thr[mid] if len(sorted_thr) % 2 == 1 else 0.5 * (sorted_thr[mid - 1] + sorted_thr[mid])

    def path_cost(nodes_path):
        total = 0.0
        for i in range(len(nodes_path) - 1):
            u = nodes_path[i]
            v = nodes_path[i + 1]
            ed = G[u][v]
            total += float(ed.get("cost", 0.0))
        return total

    def path_edges_and_through(nodes_path):
        edges = []
        thr_list = []
        for i in range(len(nodes_path) - 1):
            u = nodes_path[i]
            v = nodes_path[i + 1]
            ed = G[u][v]
            edges.append((u, v))
            thr_list.append(max(EPS_THR, float(ed.get("throughput", 0.0))))
        return edges, thr_list

    def min_bottleneck(thr_list):
        if not thr_list:
            return EPS_THR
        return min(thr_list)

    # Generate candidate paths for each destination
    candidates_by_dst = {}
    for dst in dsts:
        if dst not in G:
            candidates_by_dst[dst] = []
            continue
        cand = []
        try:
            gen = nx.shortest_simple_paths(G, src, dst, weight=lambda u, v, d: float(d.get("cost", 0.0)))
        except nx.NetworkXNoPath:
            candidates_by_dst[dst] = []
            continue

        cmin = None
        count_gen = 0
        for p in gen:
            count_gen += 1
            c = path_cost(p)
            edges, thr_list = path_edges_and_through(p)
            bthr = min_bottleneck(thr_list)
            cand.append({
                "nodes": p,
                "edges": edges,
                "thr_list": thr_list,
                "bthr": bthr,
                "cost": c,
            })
            if cmin is None or c < cmin:
                cmin = c
            # Early stop if we have enough candidates and cost drifted too far
            if len(cand) >= K_GEN_MAX and cmin is not None and c > cmin * (1.0 + SLACK_REL * 2.0) + SLACK_ABS * 2.0:
                break
            if count_gen >= K_GEN_MAX * 3:
                break

        if not cand:
            candidates_by_dst[dst] = []
            continue

        cmin_val = min(x["cost"] for x in cand)
        filtered = [x for x in cand if x["cost"] <= cmin_val * (1.0 + SLACK_REL) + SLACK_ABS]

        # Sort filtered by a combined key: lower cost, higher bottleneck throughput, fewer edges
        filtered.sort(key=lambda x: (x["cost"], -x["bthr"], len(x["edges"])))
        # Keep at most K_BASE_MAX candidates
        candidates_by_dst[dst] = filtered[:K_BASE_MAX] if filtered else cand[:1]

    # Edge and node usage tracking for overlap-aware assignment
    edge_usage = defaultdict(int)
    node_usage = defaultdict(int)

    def overlap_metric(path_entry):
        # Sum of (current usage / throughput) across edges, plus a small node reuse penalty
        edges = path_entry["edges"]
        thr_list = path_entry["thr_list"]
        score = 0.0
        for (e, thr) in zip(edges, thr_list):
            score += edge_usage[e] / max(EPS_THR, thr)
        # Node penalty for internal nodes only (excluding src and dst)
        nodes = path_entry["nodes"]
        if len(nodes) > 2:
            internal = nodes[1:-1]
            score += NODE_ALPHA * sum(node_usage[n] for n in internal)
        return score

    # Choose path for a (dst, partition) using overlap metric, tie-breakers
    def choose_path_for_dst(dst):
        cands = candidates_by_dst.get(dst, [])
        if not cands:
            return None
        # First, find minimal cost among candidates
        min_cost = min(c["cost"] for c in cands)
        # Among those within allowed slack, choose min overlap metric
        allowed = [c for c in cands if c["cost"] <= min_cost * (1.0 + SLACK_REL) + SLACK_ABS]
        if not allowed:
            allowed = cands
        # Compute metrics
        metrics = []
        for c in allowed:
            m = overlap_metric(c)
            metrics.append((m, c))
        metrics.sort(key=lambda t: (t[0], -t[1]["bthr"], len(t[1]["edges"]), t[1]["cost"]))
        return metrics[0][1] if metrics else allowed[0]

    # Interleave assignments across destinations to avoid bias
    assigned_counts = {dst: 0 for dst in dsts}
    remaining = True
    while remaining:
        remaining = False
        for dst in dsts:
            if assigned_counts[dst] >= num_partitions:
                continue
            remaining = True
            chosen = choose_path_for_dst(dst)
            if chosen is None:
                # If no path, skip (should not happen in well-formed graphs)
                assigned_counts[dst] += 1
                continue
            pid = assigned_counts[dst]
            nodes = chosen["nodes"]
            # Append edges for this partition
            for i in range(len(nodes) - 1):
                u = nodes[i]
                v = nodes[i + 1]
                bc_topology.append_dst_partition_path(dst, pid, [u, v, G[u][v]])
            # Update usage
            for e in chosen["edges"]:
                edge_usage[e] += 1
            for n in nodes[1:-1]:
                node_usage[n] += 1
            assigned_counts[dst] += 1

    return bc_topology


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        algorithm_code = """
import networkx as nx
from collections import defaultdict

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

    if src not in G:
        return bc_topology

    SLACK_REL = 0.20
    SLACK_ABS = 0.02
    K_BASE_MAX = max(1, min(12, num_partitions if num_partitions > 0 else 1))
    K_GEN_MAX = max(4, min(40, K_BASE_MAX * 4))
    EPS_THR = 1e-6
    NODE_ALPHA = 0.15

    all_thr = []
    for _, _, d in G.edges(data=True):
        thr = d.get("throughput", 0.0)
        if thr is None:
            thr = 0.0
        all_thr.append(max(EPS_THR, float(thr)))
    if not all_thr:
        thr_median = 1.0
    else:
        sorted_thr = sorted(all_thr)
        mid = len(sorted_thr) // 2
        thr_median = sorted_thr[mid] if len(sorted_thr) % 2 == 1 else 0.5 * (sorted_thr[mid - 1] + sorted_thr[mid])

    def path_cost(nodes_path):
        total = 0.0
        for i in range(len(nodes_path) - 1):
            u = nodes_path[i]
            v = nodes_path[i + 1]
            ed = G[u][v]
            total += float(ed.get("cost", 0.0))
        return total

    def path_edges_and_through(nodes_path):
        edges = []
        thr_list = []
        for i in range(len(nodes_path) - 1):
            u = nodes_path[i]
            v = nodes_path[i + 1]
            ed = G[u][v]
            edges.append((u, v))
            thr_list.append(max(EPS_THR, float(ed.get("throughput", 0.0))))
        return edges, thr_list

    def min_bottleneck(thr_list):
        if not thr_list:
            return EPS_THR
        return min(thr_list)

    candidates_by_dst = {}
    for dst in dsts:
        if dst not in G:
            candidates_by_dst[dst] = []
            continue
        cand = []
        try:
            gen = nx.shortest_simple_paths(G, src, dst, weight=lambda u, v, d: float(d.get("cost", 0.0)))
        except nx.NetworkXNoPath:
            candidates_by_dst[dst] = []
            continue

        cmin = None
        count_gen = 0
        for p in gen:
            count_gen += 1
            c = path_cost(p)
            edges, thr_list = path_edges_and_through(p)
            bthr = min_bottleneck(thr_list)
            cand.append({
                "nodes": p,
                "edges": edges,
                "thr_list": thr_list,
                "bthr": bthr,
                "cost": c,
            })
            if cmin is None or c < cmin:
                cmin = c
            if len(cand) >= K_GEN_MAX and cmin is not None and c > cmin * (1.0 + SLACK_REL * 2.0) + SLACK_ABS * 2.0:
                break
            if count_gen >= K_GEN_MAX * 3:
                break

        if not cand:
            candidates_by_dst[dst] = []
            continue

        cmin_val = min(x["cost"] for x in cand)
        filtered = [x for x in cand if x["cost"] <= cmin_val * (1.0 + SLACK_REL) + SLACK_ABS]
        filtered.sort(key=lambda x: (x["cost"], -x["bthr"], len(x["edges"])))
        candidates_by_dst[dst] = filtered[:K_BASE_MAX] if filtered else cand[:1]

    edge_usage = defaultdict(int)
    node_usage = defaultdict(int)

    def overlap_metric(path_entry):
        edges = path_entry["edges"]
        thr_list = path_entry["thr_list"]
        score = 0.0
        for (e, thr) in zip(edges, thr_list):
            score += edge_usage[e] / max(EPS_THR, thr)
        nodes = path_entry["nodes"]
        if len(nodes) > 2:
            internal = nodes[1:-1]
            score += NODE_ALPHA * sum(node_usage[n] for n in internal)
        return score

    def choose_path_for_dst(dst):
        cands = candidates_by_dst.get(dst, [])
        if not cands:
            return None
        min_cost = min(c["cost"] for c in cands)
        allowed = [c for c in cands if c["cost"] <= min_cost * (1.0 + SLACK_REL) + SLACK_ABS]
        if not allowed:
            allowed = cands
        metrics = []
        for c in allowed:
            m = overlap_metric(c)
            metrics.append((m, c))
        metrics.sort(key=lambda t: (t[0], -t[1]["bthr"], len(t[1]["edges"]), t[1]["cost"]))
        return metrics[0][1] if metrics else allowed[0]

    assigned_counts = {dst: 0 for dst in dsts}
    remaining = True
    while remaining:
        remaining = False
        for dst in dsts:
            if assigned_counts[dst] >= num_partitions:
                continue
            remaining = True
            chosen = choose_path_for_dst(dst)
            if chosen is None:
                assigned_counts[dst] += 1
                continue
            pid = assigned_counts[dst]
            nodes = chosen["nodes"]
            for i in range(len(nodes) - 1):
                u = nodes[i]
                v = nodes[i + 1]
                bc_topology.append_dst_partition_path(dst, pid, [u, v, G[u][v]])
            for e in chosen["edges"]:
                edge_usage[e] += 1
            for n in nodes[1:-1]:
                node_usage[n] += 1
            assigned_counts[dst] += 1

    return bc_topology
"""
        return {"code": algorithm_code}
