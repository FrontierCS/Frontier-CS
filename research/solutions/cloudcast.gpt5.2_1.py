import json
import os
from typing import Optional, Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        if spec_path:
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    spec = json.load(f)
                if isinstance(spec, dict) and "num_vms" in spec:
                    num_vms = int(spec["num_vms"])
            except Exception:
                num_vms = 2

        code = f'''
import math
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Callable, Optional

import networkx as nx
from networkx.algorithms.tree.branchings import Edmonds


class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {{dst: {{str(i): None for i in range(self.num_partitions)}} for dst in dsts}}

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


def _provider(node: str) -> str:
    if not isinstance(node, str):
        return ""
    i = node.find(":")
    if i <= 0:
        return node.lower()
    return node[:i].lower()


def _limits(num_vms: int):
    ingress = {{
        "aws": 10.0,
        "gcp": 16.0,
        "azure": 16.0
    }}
    egress = {{
        "aws": 5.0,
        "gcp": 7.0,
        "azure": 16.0
    }}
    # multiply by vm count
    for k in list(ingress.keys()):
        ingress[k] = ingress[k] * num_vms
    for k in list(egress.keys()):
        egress[k] = egress[k] * num_vms
    return ingress, egress


def _make_weight(tau: float) -> Callable:
    eps = 1e-12
    def w(u, v, data):
        c = float(data.get("cost", 0.0))
        t = float(data.get("throughput", 0.0))
        if tau <= 0.0:
            return c
        if t <= eps:
            return c + tau / eps
        return c + tau / t
    return w


def _paths_from_spt(src: str, dsts: List[str], G: nx.DiGraph, weight_fn: Callable) -> Optional[Dict[str, List[str]]]:
    try:
        dist, paths = nx.single_source_dijkstra(G, src, weight=weight_fn)
    except Exception:
        return None
    out = {{}}
    for d in dsts:
        p = paths.get(d)
        if not p or p[0] != src or p[-1] != d:
            return None
        out[d] = p
    return out


def _terminal_arborescence_paths(src: str, dsts: List[str], G: nx.DiGraph, weight_fn: Callable,
                                degree_balance: bool = False, target_thr: float = 2.0,
                                deg_pen_scale: float = 0.02, iters: int = 4) -> Optional[Dict[str, List[str]]]:
    terminals = [src] + [d for d in dsts if d != src]
    # avoid huge closure if too many terminals
    if len(terminals) > 70:
        return None

    # Precompute shortest paths from each terminal to all nodes
    distT: Dict[str, Dict[str, float]] = {{}}
    pathT: Dict[str, Dict[str, List[str]]] = {{}}
    for t in terminals:
        try:
            dist, paths = nx.single_source_dijkstra(G, t, weight=weight_fn)
        except Exception:
            return None
        distT[t] = dist
        pathT[t] = paths

    # Build closure digraph on terminals
    BIG = 1e9
    H = nx.DiGraph()
    for u in terminals:
        H.add_node(u)
    base_w: Dict[Tuple[str, str], float] = {{}}
    for u in terminals:
        du = distT[u]
        for v in terminals:
            if u == v:
                continue
            dv = du.get(v, math.inf)
            if not math.isfinite(dv):
                continue
            w = dv
            if v == src:
                w = BIG
            base_w[(u, v)] = w
            H.add_edge(u, v, weight=w)

    if not all(H.in_degree(t) > 0 or t == src for t in terminals):
        # no arborescence possible
        return None

    ingress_lim, egress_lim = _limits({int(num_vms)})

    def cap_out(node: str) -> int:
        prov = _provider(node)
        lim = egress_lim.get(prov, 1e9)
        if not math.isfinite(lim) or lim <= 0:
            return 1
        if target_thr <= 0:
            return 1
        return max(1, int(lim // target_thr))

    caps = {{t: cap_out(t) for t in terminals}}
    # degree penalty coefficient per node (scaled by egress limit)
    deg_pen = {{}}
    for t in terminals:
        prov = _provider(t)
        lim = egress_lim.get(prov, 1e9)
        if not math.isfinite(lim) or lim <= 0:
            deg_pen[t] = 0.0
        else:
            deg_pen[t] = float(deg_pen_scale) / lim

    last_out = None
    bestA = None

    for _ in range(max(1, iters if degree_balance else 1)):
        try:
            A = Edmonds(H).find_optimum(attr="weight", default=BIG, kind="min", style="arborescence", preserve_attrs=True)
        except Exception:
            return None

        # ensure src is root (in_degree 0)
        if A.in_degree(src) != 0:
            # If root not src, likely due to connectivity/weights. Give up.
            return None

        bestA = A

        if not degree_balance:
            break

        outdeg = {n: A.out_degree(n) for n in terminals}
        if last_out == outdeg:
            break
        last_out = outdeg

        # Update weights with degree penalty
        for (u, v), bw in base_w.items():
            penalty = 0.0
            od = outdeg.get(u, 0)
            cap = caps.get(u, 1)
            if od >= cap + 1:
                penalty = (od - cap) * deg_pen.get(u, 0.0)
            H[u][v]["weight"] = bw + penalty

    if bestA is None:
        return None

    parent: Dict[str, str] = {{}}
    for v in terminals:
        if v == src:
            continue
        preds = list(bestA.predecessors(v))
        if not preds:
            return None
        parent[v] = preds[0]

    # Build terminal chain -> expanded node path for each dst
    def term_chain(d: str) -> Optional[List[str]]:
        if d == src:
            return [src]
        if d not in parent:
            return None
        chain = []
        seen = set()
        cur = d
        while cur != src:
            if cur in seen:
                return None
            seen.add(cur)
            chain.append(cur)
            cur = parent.get(cur)
            if cur is None:
                return None
        chain.append(src)
        chain.reverse()
        return chain

    paths_by_dst: Dict[str, List[str]] = {{}}
    for d in dsts:
        chain = term_chain(d)
        if not chain:
            return None
        full = None
        for i in range(len(chain) - 1):
            u, v = chain[i], chain[i + 1]
            pv = pathT.get(u, {{}}).get(v)
            if not pv or pv[0] != u or pv[-1] != v:
                return None
            if full is None:
                full = list(pv)
            else:
                full.extend(pv[1:])
        if not full or full[0] != src or full[-1] != d:
            return None
        paths_by_dst[d] = full
    return paths_by_dst


def _objective(paths_by_dst: Dict[str, List[str]], G: nx.DiGraph, num_vms: int) -> float:
    if not paths_by_dst:
        return float("inf")
    edge_set = set()
    node_set = set()
    for p in paths_by_dst.values():
        if not p:
            return float("inf")
        for n in p:
            node_set.add(n)
        for i in range(len(p) - 1):
            u, v = p[i], p[i + 1]
            if u == v:
                return float("inf")
            if not G.has_edge(u, v):
                return float("inf")
            edge_set.add((u, v))
    if not edge_set:
        return float("inf")

    outdeg = defaultdict(int)
    indeg = defaultdict(int)
    for u, v in edge_set:
        outdeg[u] += 1
        indeg[v] += 1

    ingress_lim, egress_lim = _limits(num_vms)

    sum_cost = 0.0
    f_min = float("inf")
    for u, v in edge_set:
        data = G[u][v]
        c = float(data.get("cost", 0.0))
        thr = float(data.get("throughput", 0.0))
        if thr <= 0.0:
            thr = 1e-12

        pu = _provider(u)
        pv = _provider(v)
        lim_out = egress_lim.get(pu, 1e9)
        lim_in = ingress_lim.get(pv, 1e9)

        od = outdeg.get(u, 1)
        idd = indeg.get(v, 1)
        cap_out = lim_out / max(1, od) if lim_out > 0 else 1e-12
        cap_in = lim_in / max(1, idd) if lim_in > 0 else 1e-12

        f = min(thr, cap_out, cap_in)
        if f <= 0.0:
            return float("inf")
        if f < f_min:
            f_min = f
        sum_cost += c

    # per-GB instance coefficient
    gamma = num_vms * 0.54 * 8.0 / 3600.0
    inst_term = (len(node_set) * gamma) / max(1e-12, f_min)
    return sum_cost + inst_term


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    num_partitions = int(num_partitions)
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    if not dsts or num_partitions <= 0:
        return bc_topology

    # Deduplicate dsts while preserving order
    seen = set()
    dsts_u = []
    for d in dsts:
        if d not in seen:
            seen.add(d)
            dsts_u.append(d)
    dsts = dsts_u

    # If any dst equals src, give empty paths
    for d in dsts:
        if d == src:
            for p in range(num_partitions):
                bc_topology.set_dst_partition_paths(d, p, [])
    real_dsts = [d for d in dsts if d != src]
    if not real_dsts:
        return bc_topology

    # Candidate generation
    candidates = []

    # SPT - pure cost
    w0 = _make_weight(0.0)
    spt0 = _paths_from_spt(src, real_dsts, G, w0)
    if spt0 is not None:
        candidates.append(("spt_cost", spt0))

    # SPT - cost + throughput
    wt = _make_weight(0.002)
    sptt = _paths_from_spt(src, real_dsts, G, wt)
    if sptt is not None:
        candidates.append(("spt_cost_thr", sptt))

    # Terminal arborescence - pure cost
    term0 = _terminal_arborescence_paths(src, real_dsts, G, w0, degree_balance=False)
    if term0 is not None:
        candidates.append(("term_cost", term0))

    # Terminal arborescence - throughput + degree balance
    termt = _terminal_arborescence_paths(src, real_dsts, G, wt, degree_balance=True, target_thr=2.0, deg_pen_scale=0.02, iters=4)
    if termt is not None:
        candidates.append(("term_bal_thr", termt))

    if not candidates:
        # last resort: per-dst shortest by cost (not necessarily shared)
        for d in real_dsts:
            try:
                path = nx.dijkstra_path(G, src, d, weight="cost")
            except Exception:
                path = None
            if not path:
                # still must set something; leave as empty (will likely fail evaluator)
                for p in range(num_partitions):
                    bc_topology.set_dst_partition_paths(d, p, [])
                continue
            edges = [[path[i], path[i + 1], G[path[i]][path[i + 1]]] for i in range(len(path) - 1)]
            for p in range(num_partitions):
                bc_topology.set_dst_partition_paths(d, p, list(edges))
        return bc_topology

    # Choose best candidate by approximate per-GB objective
    best_name = None
    best_paths = None
    best_obj = float("inf")
    for name, paths_by_dst in candidates:
        obj = _objective(paths_by_dst, G, {int(num_vms)})
        if obj < best_obj:
            best_obj = obj
            best_name = name
            best_paths = paths_by_dst

    # Build final topology
    for d in real_dsts:
        nodes = best_paths.get(d)
        if not nodes:
            # fallback to direct shortest path cost
            try:
                nodes = nx.dijkstra_path(G, src, d, weight="cost")
            except Exception:
                nodes = None
        if not nodes or nodes[0] != src or nodes[-1] != d:
            # still invalid
            for p in range(num_partitions):
                bc_topology.set_dst_partition_paths(d, p, [])
            continue

        edges = []
        ok = True
        for i in range(len(nodes) - 1):
            u, v = nodes[i], nodes[i + 1]
            if u == v or not G.has_edge(u, v):
                ok = False
                break
            edges.append([u, v, G[u][v]])
        if not ok:
            for p in range(num_partitions):
                bc_topology.set_dst_partition_paths(d, p, [])
            continue

        for p in range(num_partitions):
            bc_topology.set_dst_partition_paths(d, p, list(edges))

    return bc_topology
'''
        return {"code": code}