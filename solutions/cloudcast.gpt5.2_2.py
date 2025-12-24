import json
import os
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        ingress_limit = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
        egress_limit = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}

        if spec_path:
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    spec = json.load(f)
                if isinstance(spec, dict):
                    num_vms = int(spec.get("num_vms", num_vms) or num_vms)

                    cfg_files = spec.get("config_files", []) or []
                    if isinstance(cfg_files, list) and cfg_files:
                        base_dir = os.path.dirname(os.path.abspath(spec_path))
                        ing_seen = []
                        eg_seen = []
                        for p in cfg_files:
                            if not isinstance(p, str):
                                continue
                            cp = p
                            if not os.path.isabs(cp):
                                cp = os.path.join(base_dir, cp)
                            try:
                                with open(cp, "r", encoding="utf-8") as cf:
                                    cfg = json.load(cf)
                                if isinstance(cfg, dict):
                                    if isinstance(cfg.get("ingress_limit"), dict):
                                        ing_seen.append(cfg["ingress_limit"])
                                    if isinstance(cfg.get("egress_limit"), dict):
                                        eg_seen.append(cfg["egress_limit"])
                            except Exception:
                                continue

                        def _all_same_dict(dicts):
                            if not dicts:
                                return None
                            first = dicts[0]
                            for d in dicts[1:]:
                                if d != first:
                                    return None
                            return first

                        ing_u = _all_same_dict(ing_seen)
                        eg_u = _all_same_dict(eg_seen)
                        if ing_u:
                            ingress_limit = {k.lower(): float(v) for k, v in ing_u.items()}
                        if eg_u:
                            egress_limit = {k.lower(): float(v) for k, v in eg_u.items()}
            except Exception:
                pass

        code = f"""
import networkx as nx

NUM_VMS = {int(num_vms)}
INSTANCE_RATE_PER_HOUR = 0.54

INGRESS_LIMIT = {json.dumps({k: float(v) for k, v in ingress_limit.items()})}
EGRESS_LIMIT = {json.dumps({k: float(v) for k, v in egress_limit.items()})}

def _provider(node: str) -> str:
    if not isinstance(node, str):
        return "unknown"
    i = node.find(":")
    if i <= 0:
        return node.lower()
    return node[:i].lower()

def _median(vals):
    vals = [v for v in vals if v is not None]
    n = len(vals)
    if n == 0:
        return 0.0
    vals.sort()
    mid = n // 2
    if n & 1:
        return float(vals[mid])
    return 0.5 * (float(vals[mid - 1]) + float(vals[mid]))

def _build_tree_paths(src: str, dsts, G: nx.DiGraph, weight_func):
    paths = {{}}
    try:
        all_paths = nx.single_source_dijkstra_path(G, src, weight=weight_func)
    except Exception:
        all_paths = {{}}
    for d in dsts:
        p = all_paths.get(d)
        if not p:
            try:
                p = nx.dijkstra_path(G, src, d, weight=weight_func)
            except Exception:
                try:
                    p = nx.shortest_path(G, src, d)
                except Exception:
                    p = None
        paths[d] = p
    return paths

def _tree_from_dst_paths(dst_paths, G: nx.DiGraph):
    edges = set()
    nodes = set()
    for d, p in dst_paths.items():
        if not p or len(p) < 2:
            continue
        nodes.update(p)
        for i in range(len(p) - 1):
            u = p[i]; v = p[i + 1]
            if u == v:
                continue
            if G.has_edge(u, v):
                edges.add((u, v))
    for (u, v) in edges:
        nodes.add(u); nodes.add(v)
    return {{"paths": dst_paths, "edges": edges, "nodes": nodes}}

def _effective_throughputs(used_edges, G: nx.DiGraph):
    out_deg = {{}}
    in_deg = {{}}
    nodes = set()
    for (u, v) in used_edges:
        nodes.add(u); nodes.add(v)
        out_deg[u] = out_deg.get(u, 0) + 1
        in_deg[v] = in_deg.get(v, 0) + 1

    egress_share = {{}}
    ingress_share = {{}}
    for n in nodes:
        prov = _provider(n)
        el = float(EGRESS_LIMIT.get(prov, 1e18)) * float(NUM_VMS)
        il = float(INGRESS_LIMIT.get(prov, 1e18)) * float(NUM_VMS)
        od = out_deg.get(n, 0)
        idg = in_deg.get(n, 0)
        egress_share[n] = (el / od) if od > 0 else 1e18
        ingress_share[n] = (il / idg) if idg > 0 else 1e18

    eff = {{}}
    for (u, v) in used_edges:
        data = G[u][v]
        tp = data.get("throughput", 1e18)
        try:
            tp = float(tp)
        except Exception:
            tp = 1e18
        f = tp
        es = egress_share.get(u, 1e18)
        is_ = ingress_share.get(v, 1e18)
        if es < f:
            f = es
        if is_ < f:
            f = is_
        eff[(u, v)] = f
    return eff, nodes

def _eval_counts(trees, counts, G: nx.DiGraph):
    edge_cnt = {{}}
    used_edges = set()
    used_nodes = set()
    for t, c in enumerate(counts):
        if c <= 0:
            continue
        for e in trees[t]["edges"]:
            edge_cnt[e] = edge_cnt.get(e, 0) + c
            used_edges.add(e)
        used_nodes |= trees[t]["nodes"]

    if not used_edges:
        return 1e30

    eff_tp, deg_nodes = _effective_throughputs(used_edges, G)
    used_nodes |= deg_nodes

    egress_metric = 0.0
    max_ratio = 0.0
    eps = 1e-12
    for (u, v), pc in edge_cnt.items():
        data = G[u][v]
        c = data.get("cost", 0.0)
        try:
            c = float(c)
        except Exception:
            c = 0.0
        egress_metric += float(pc) * c

        f = eff_tp.get((u, v), 0.0)
        if f <= 0:
            ratio = 1e30
        else:
            ratio = float(pc) / max(float(f), eps)
        if ratio > max_ratio:
            max_ratio = ratio

    node_count = len(used_nodes)
    gamma = float(NUM_VMS) * float(INSTANCE_RATE_PER_HOUR) / 3600.0 * 8.0
    obj = egress_metric + gamma * float(node_count) * float(max_ratio)
    return obj

def _best_counts(trees, num_partitions: int, G: nx.DiGraph):
    m = len(trees)
    n = int(num_partitions)
    if m <= 1:
        return [n]
    best_obj = 1e300
    best = None

    if m == 2:
        for c0 in range(n + 1):
            c1 = n - c0
            counts = [c0, c1]
            obj = _eval_counts(trees, counts, G)
            if obj < best_obj:
                best_obj = obj
                best = counts
        return best

    if m == 3:
        for c0 in range(n + 1):
            rem0 = n - c0
            for c1 in range(rem0 + 1):
                c2 = rem0 - c1
                counts = [c0, c1, c2]
                obj = _eval_counts(trees, counts, G)
                if obj < best_obj:
                    best_obj = obj
                    best = counts
        return best

    # m >= 4: cap at 4 for distribution, extra trees ignored
    m = 4
    trees = trees[:4]
    for c0 in range(n + 1):
        rem0 = n - c0
        for c1 in range(rem0 + 1):
            rem1 = rem0 - c1
            for c2 in range(rem1 + 1):
                c3 = rem1 - c2
                counts = [c0, c1, c2, c3]
                obj = _eval_counts(trees, counts, G)
                if obj < best_obj:
                    best_obj = obj
                    best = counts
    return best

def _choose_best_relay_tree(src: str, dsts, G: nx.DiGraph):
    # Candidate relays: closest to src by cost, prefer those that can reach all dsts
    try:
        lens = nx.single_source_dijkstra_path_length(G, src, weight="cost")
    except Exception:
        lens = {{}}
    if not lens:
        return None

    candidates = []
    for n, d in lens.items():
        if n == src:
            continue
        try:
            candidates.append((float(d), n))
        except Exception:
            continue
    candidates.sort()
    candidates = [n for _, n in candidates[:15]]
    if not candidates:
        return None

    best_tree = None
    best_obj = 1e300

    # Precompute src->relay paths by cost
    try:
        src_paths = nx.single_source_dijkstra_path(G, src, weight="cost")
    except Exception:
        src_paths = {{}}

    for r in candidates:
        p_sr = src_paths.get(r)
        if not p_sr:
            continue
        try:
            r_paths = nx.single_source_dijkstra_path(G, r, weight="cost")
        except Exception:
            continue
        ok = True
        dst_paths = {{}}
        for d in dsts:
            p_rd = r_paths.get(d)
            if not p_rd:
                ok = False
                break
            if len(p_sr) >= 2:
                full = p_sr[:-1] + p_rd
            else:
                full = p_rd
            dst_paths[d] = full
        if not ok:
            continue

        tree = _tree_from_dst_paths(dst_paths, G)
        # Evaluate as a standalone tree with all partitions on it (counts handled outside too)
        obj = _eval_counts([tree], [10], G)  # use fixed count to compare relays independent-ish
        if obj < best_obj:
            best_obj = obj
            best_tree = tree

    return best_tree

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int):
    num_partitions = int(num_partitions)
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Basic stats
    costs = []
    tps = []
    for u, v, d in G.edges(data=True):
        try:
            costs.append(float(d.get("cost", 0.0)))
        except Exception:
            pass
        try:
            tps.append(float(d.get("throughput", 0.0)))
        except Exception:
            pass
    cost_med = _median(costs) if costs else 0.001
    if cost_med <= 0:
        cost_med = 0.001
    tp_med = _median([x for x in tps if x > 0]) if tps else 10.0
    if tp_med <= 0:
        tp_med = 10.0

    rho = cost_med * tp_med * 0.5
    penalty_add = cost_med * 10.0

    def w_cost(u, v, d):
        c = d.get("cost", 0.0)
        try:
            return float(c)
        except Exception:
            return 0.0

    def w_cost_tp(u, v, d):
        c = d.get("cost", 0.0)
        tp = d.get("throughput", tp_med)
        try:
            c = float(c)
        except Exception:
            c = 0.0
        try:
            tp = float(tp)
        except Exception:
            tp = tp_med
        if tp <= 0:
            tp = 1e-9
        return c + rho / tp

    # Tree 0: cost-only
    dst_paths0 = _build_tree_paths(src, dsts, G, w_cost)
    tree0 = _tree_from_dst_paths(dst_paths0, G)
    edges0 = tree0["edges"]

    # Tree 1: cost + throughput
    dst_paths1 = _build_tree_paths(src, dsts, G, w_cost_tp)
    tree1 = _tree_from_dst_paths(dst_paths1, G)

    # Tree 2: penalize tree0 edges + throughput
    def w_penalized(u, v, d):
        base = w_cost_tp(u, v, d)
        if (u, v) in edges0:
            base += penalty_add * (3.0 if u == src else 1.0)
        return base

    dst_paths2 = _build_tree_paths(src, dsts, G, w_penalized)
    tree2 = _tree_from_dst_paths(dst_paths2, G)

    trees = [tree0, tree1, tree2]

    relay_tree = _choose_best_relay_tree(src, dsts, G)
    if relay_tree is not None and relay_tree["edges"]:
        trees.append(relay_tree)

    # De-duplicate identical trees (by edges)
    uniq = []
    seen = set()
    for t in trees:
        key = tuple(sorted(t["edges"]))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(t)
    trees = uniq
    if not trees:
        # Fallback: per-dst shortest path cost-only, no sharing across dsts
        for d in dsts:
            try:
                p = nx.dijkstra_path(G, src, d, weight="cost")
            except Exception:
                p = nx.shortest_path(G, src, d)
            edges = []
            for i in range(len(p) - 1):
                edges.append([p[i], p[i + 1], G[p[i]][p[i + 1]]])
            for part in range(num_partitions):
                bc_topology.set_dst_partition_paths(d, part, edges)
        return bc_topology

    best_counts = _best_counts(trees, num_partitions, G)
    if best_counts is None:
        best_counts = [num_partitions] + [0] * (len(trees) - 1)

    # Build partition -> tree assignment
    part_to_tree = [0] * num_partitions
    idx = 0
    for t, c in enumerate(best_counts):
        for _ in range(int(c)):
            if idx >= num_partitions:
                break
            part_to_tree[idx] = t
            idx += 1
        if idx >= num_partitions:
            break
    # If some partitions unassigned due to truncation, put them on tree0
    while idx < num_partitions:
        part_to_tree[idx] = 0
        idx += 1

    # Fill topology
    for part in range(num_partitions):
        t = part_to_tree[part]
        tpaths = trees[t]["paths"]
        for d in dsts:
            p = tpaths.get(d)
            if not p:
                # Fallback for missing path
                try:
                    p = nx.dijkstra_path(G, src, d, weight="cost")
                except Exception:
                    p = nx.shortest_path(G, src, d)
            edges = []
            for i in range(len(p) - 1):
                u = p[i]; v = p[i + 1]
                if u == v:
                    continue
                edges.append([u, v, G[u][v]])
            bc_topology.set_dst_partition_paths(d, part, edges)

    return bc_topology


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
"""
        return {"code": code}
