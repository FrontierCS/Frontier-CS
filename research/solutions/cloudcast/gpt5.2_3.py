import json
import os
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        ingress_limit = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
        egress_limit = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}
        s_partition_est = 30.0  # GB, default guess

        if spec_path:
            try:
                with open(spec_path, "r") as f:
                    spec = json.load(f)
                if isinstance(spec, dict):
                    num_vms = int(spec.get("num_vms", num_vms) or num_vms)
                    cfgs = spec.get("config_files", []) or []
                    sizes = []
                    ingress_seen = []
                    egress_seen = []
                    for cfg_path in cfgs:
                        try:
                            with open(cfg_path, "r") as cf:
                                cfg = json.load(cf)
                            if isinstance(cfg, dict):
                                dv = float(cfg.get("data_vol", 0.0) or 0.0)
                                np = int(cfg.get("num_partitions", 0) or 0)
                                if dv > 0 and np > 0:
                                    sizes.append(dv / np)
                                ing = cfg.get("ingress_limit", None)
                                eg = cfg.get("egress_limit", None)
                                if isinstance(ing, dict):
                                    ingress_seen.append(ing)
                                if isinstance(eg, dict):
                                    egress_seen.append(eg)
                        except Exception:
                            continue
                    if sizes:
                        s_partition_est = sum(sizes) / max(1, len(sizes))
                    if ingress_seen:
                        merged = dict(ingress_limit)
                        for d in ingress_seen:
                            for k, v in d.items():
                                try:
                                    merged[str(k).lower()] = float(v)
                                except Exception:
                                    pass
                        ingress_limit = merged
                    if egress_seen:
                        merged = dict(egress_limit)
                        for d in egress_seen:
                            for k, v in d.items():
                                try:
                                    merged[str(k).lower()] = float(v)
                                except Exception:
                                    pass
                        egress_limit = merged
            except Exception:
                pass

        algo_code = f"""import math
import heapq
from collections import defaultdict
import networkx as nx
import zlib


N_VMS = {int(num_vms)}
INSTANCE_RATE_PER_HOUR = 0.54
INSTANCE_RATE_PER_SEC_PER_VM = INSTANCE_RATE_PER_HOUR / 3600.0

INGRESS_LIMIT = {repr({k.lower(): float(v) for k, v in ingress_limit.items()})}
EGRESS_LIMIT = {repr({k.lower(): float(v) for k, v in egress_limit.items()})}

S_PARTITION_EST_GB = {float(s_partition_est)}


def _provider(node: str) -> str:
    if not node:
        return ""
    i = node.find(":")
    if i <= 0:
        return str(node).lower()
    return node[:i].lower()


def _limit_ingress(node: str) -> float:
    return float(INGRESS_LIMIT.get(_provider(node), 1e9))


def _limit_egress(node: str) -> float:
    return float(EGRESS_LIMIT.get(_provider(node), 1e9))


def _median(vals):
    if not vals:
        return 0.0
    a = sorted(vals)
    n = len(a)
    m = n // 2
    if n % 2 == 1:
        return float(a[m])
    return 0.5 * (float(a[m - 1]) + float(a[m]))


def _edge_noise(u: str, v: str, seed: int) -> float:
    s = (u + "|" + v + "|" + str(seed)).encode("utf-8", "ignore")
    x = zlib.crc32(s) & 0xFFFFFFFF
    # map to [-1, 1]
    return (x / 2147483647.5) - 1.0


def _build_weight_map(G: nx.DiGraph, mode: int, med_cost: float, med_thr: float, seed: int):
    # mode:
    # 0: cost + hop
    # 1: cost + hop + lam*(1/thr)
    # 2: cost + hop + lam2*(1/thr)
    # 3: cost*(1+noise) + hop + lam*(1/thr)
    eps = 1e-9
    hop = max(0.0, med_cost * 0.02)
    lam_base = max(0.0, med_cost * max(med_thr, 1.0))
    if mode == 0:
        lam = 0.0
        noise_scale = 0.0
    elif mode == 1:
        lam = lam_base * 0.5
        noise_scale = 0.0
    elif mode == 2:
        lam = lam_base * 1.5
        noise_scale = 0.0
    else:
        lam = lam_base * 0.8
        noise_scale = 0.10  # relative to cost
    w = {{}}
    for u, v, data in G.edges(data=True):
        c = float(data.get("cost", 0.0) or 0.0)
        thr = float(data.get("throughput", 0.0) or 0.0)
        inv_thr = 1.0 / max(thr, eps)
        ww = c + hop + lam * inv_thr
        if noise_scale:
            ww = (c * (1.0 + noise_scale * _edge_noise(u, v, seed))) + hop + lam * inv_thr
        if ww < 0.0:
            ww = 0.0
        w[(u, v)] = ww
    return w


def _dijkstra_pred(G: nx.DiGraph, src: str, weight_map: dict):
    INF = 1e100
    dist = {{src: 0.0}}
    pred = {{}}
    heap = [(0.0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist.get(u, INF):
            continue
        for v, attr in G.adj[u].items():
            w = weight_map.get((u, v), None)
            if w is None:
                c = float(attr.get("cost", 0.0) or 0.0)
                thr = float(attr.get("throughput", 0.0) or 0.0)
                w = c + (0.0 if thr <= 0 else 0.0)
            nd = d + w
            old = dist.get(v, INF)
            if nd + 1e-12 < old:
                dist[v] = nd
                pred[v] = u
                heapq.heappush(heap, (nd, v))
            elif abs(nd - old) <= 1e-12:
                # tie-breaker: prefer predecessor with smaller dist (should be) then lexicographically smaller
                pu = pred.get(v, None)
                if pu is None or str(u) < str(pu):
                    pred[v] = u
    return pred, dist


def _reconstruct_path_edges(G: nx.DiGraph, pred: dict, src: str, dst: str):
    if src == dst:
        return []
    cur = dst
    nodes = []
    seen = set()
    while cur != src:
        if cur in seen:
            return None
        seen.add(cur)
        p = pred.get(cur, None)
        if p is None:
            return None
        nodes.append(cur)
        cur = p
    nodes.append(src)
    nodes.reverse()
    edges = []
    for i in range(len(nodes) - 1):
        u = nodes[i]
        v = nodes[i + 1]
        if u == v:
            return None
        try:
            edges.append([u, v, G[u][v]])
        except Exception:
            return None
    return edges


def _tree_from_weights(G: nx.DiGraph, src: str, dsts: list, weight_map: dict):
    pred, _ = _dijkstra_pred(G, src, weight_map)
    dst_paths = {{}}
    edges_set = set()
    nodes_set = set([src])
    for d in dsts:
        pe = _reconstruct_path_edges(G, pred, src, d)
        if pe is None:
            return None
        dst_paths[d] = pe
        for u, v, _data in pe:
            edges_set.add((u, v))
            nodes_set.add(u)
            nodes_set.add(v)
    sum_cost = 0.0
    for (u, v) in edges_set:
        try:
            sum_cost += float(G[u][v].get("cost", 0.0) or 0.0)
        except Exception:
            pass
    return {{
        "dst_paths": dst_paths,
        "edges": edges_set,
        "nodes": nodes_set,
        "sum_cost": sum_cost,
    }}


def _effective_bw(u: str, v: str, thr: float, out_deg: dict, in_deg: dict):
    eff = float(thr)
    if eff <= 0.0:
        eff = 1e-9
    od = out_deg.get(u, 1)
    idg = in_deg.get(v, 1)
    if od <= 0:
        od = 1
    if idg <= 0:
        idg = 1
    out_lim = _limit_egress(u) * float(N_VMS)
    in_lim = _limit_ingress(v) * float(N_VMS)
    share_out = out_lim / float(od)
    share_in = in_lim / float(idg)
    if share_out < eff:
        eff = share_out
    if share_in < eff:
        eff = share_in
    if eff <= 1e-9:
        eff = 1e-9
    return eff


def _estimate_total_cost(G: nx.DiGraph, trees: list, counts: tuple):
    # Build edge partition counts and used edges set
    edge_k = defaultdict(int)
    used_edges = set()
    used_nodes = set()
    for j, c in enumerate(counts):
        if c <= 0:
            continue
        t = trees[j]
        used_nodes |= t["nodes"]
        for e in t["edges"]:
            edge_k[e] += int(c)
            used_edges.add(e)

    if not used_edges:
        return 0.0

    out_deg = defaultdict(int)
    in_deg = defaultdict(int)
    for (u, v) in used_edges:
        out_deg[u] += 1
        in_deg[v] += 1

    # Compute makespan time and egress
    time_s = 0.0
    egress_cost = 0.0
    S = float(S_PARTITION_EST_GB)
    for (u, v), k in edge_k.items():
        try:
            data = G[u][v]
            c = float(data.get("cost", 0.0) or 0.0)
            thr = float(data.get("throughput", 0.0) or 0.0)
        except Exception:
            c = 0.0
            thr = 1e-9
        egress_cost += c * float(k) * S
        eff = _effective_bw(u, v, thr, out_deg, in_deg)
        t = (float(k) * S * 8.0) / eff
        if t > time_s:
            time_s = t

    node_count = len(used_nodes)
    instance_cost = float(node_count) * float(N_VMS) * float(INSTANCE_RATE_PER_SEC_PER_VM) * float(time_s)
    return float(egress_cost) + float(instance_cost)


def _gen_compositions(n: int, k: int):
    # yields tuples of length k summing to n
    if k <= 1:
        yield (n,)
        return
    if k == 2:
        for a in range(n + 1):
            yield (a, n - a)
        return
    # recursion for k up to 4
    def rec(rem, idx, cur):
        if idx == k - 1:
            yield tuple(cur + [rem])
            return
        for x in range(rem + 1):
            cur.append(x)
            yield from rec(rem - x, idx + 1, cur)
            cur.pop()
    yield from rec(n, 0, [])


class BroadCastTopology:
    def __init__(self, src: str, dsts: list, num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {{dst: {{str(i): None for i in range(self.num_partitions)}} for dst in dsts}}

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


def search_algorithm(src: str, dsts: list, G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    num_partitions = int(num_partitions)
    bc = BroadCastTopology(src, dsts, num_partitions)
    if num_partitions <= 0 or not dsts:
        return bc

    # Precompute medians for weight scaling
    costs = []
    thrs = []
    for _u, _v, data in G.edges(data=True):
        try:
            costs.append(float(data.get("cost", 0.0) or 0.0))
        except Exception:
            pass
        try:
            thrs.append(float(data.get("throughput", 0.0) or 0.0))
        except Exception:
            pass
    med_cost = _median(costs) if costs else 0.01
    med_thr = _median([t for t in thrs if t > 0]) if thrs else 10.0
    if med_cost <= 0.0:
        med_cost = 0.01
    if med_thr <= 0.0:
        med_thr = 10.0

    # Build candidate trees
    candidates = []
    seen = set()
    max_modes = 4
    for mode in range(max_modes):
        wmap = _build_weight_map(G, mode, med_cost, med_thr, seed=1337 + mode * 97)
        t = _tree_from_weights(G, src, dsts, wmap)
        if t is None:
            continue
        key = frozenset(t["edges"])
        if key in seen:
            continue
        seen.add(key)
        candidates.append(t)
        if len(candidates) >= 4:
            break

    if not candidates:
        # Fallback: direct cost-based shortest paths per-destination per-partition (no multicast optimization)
        for dst in dsts:
            try:
                nodes = nx.dijkstra_path(G, src, dst, weight="cost")
            except Exception:
                nodes = None
            if not nodes or len(nodes) < 2:
                nodes = [src, dst] if G.has_edge(src, dst) else [src]
            edges = []
            ok = True
            for i in range(len(nodes) - 1):
                u = nodes[i]
                v = nodes[i + 1]
                if u == v or not G.has_edge(u, v):
                    ok = False
                    break
                edges.append([u, v, G[u][v]])
            if not ok:
                edges = []
            for p in range(num_partitions):
                bc.set_dst_partition_paths(dst, p, edges)
        return bc

    K = min(len(candidates), max(1, min(4, num_partitions)))
    trees = candidates[:K]

    # Choose best distribution among candidate trees
    best_counts = None
    best_cost = float("inf")

    # If extremely large, use greedy instead of full enumeration
    do_enum = (num_partitions <= 40 and K <= 4)

    if do_enum:
        for counts in _gen_compositions(num_partitions, K):
            total = _estimate_total_cost(G, trees, counts)
            if total < best_cost:
                best_cost = total
                best_counts = counts
    else:
        # Greedy fallback
        counts = [0] * K
        for _p in range(num_partitions):
            best_j = 0
            best = float("inf")
            for j in range(K):
                trial = list(counts)
                trial[j] += 1
                total = _estimate_total_cost(G, trees, tuple(trial))
                if total < best:
                    best = total
                    best_j = j
            counts[best_j] += 1
        best_counts = tuple(counts)

    # Assign partitions to trees according to best_counts
    part_to_tree = [0] * num_partitions
    idx = 0
    for j, c in enumerate(best_counts):
        for p in range(idx, min(num_partitions, idx + int(c))):
            part_to_tree[p] = j
        idx += int(c)

    # Fill broadcast topology paths
    for p in range(num_partitions):
        tj = part_to_tree[p]
        dst_paths = trees[tj]["dst_paths"]
        for dst in dsts:
            bc.set_dst_partition_paths(dst, p, dst_paths[dst])

    return bc
"""
        return {"code": algo_code}