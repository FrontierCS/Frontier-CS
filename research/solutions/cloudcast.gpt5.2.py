import json
import os
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        assumed_data_vol = 300.0
        ingress_limit = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
        egress_limit = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}

        if spec_path:
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    spec = json.load(f)
                if isinstance(spec, dict) and "num_vms" in spec:
                    try:
                        num_vms = int(spec["num_vms"])
                    except Exception:
                        pass

                cfg_files = spec.get("config_files", []) if isinstance(spec, dict) else []
                base_dir = os.path.dirname(os.path.abspath(spec_path))
                data_vols = []
                ingress_candidates = []
                egress_candidates = []

                for cf in cfg_files:
                    try:
                        cfg_path = cf
                        if not os.path.isabs(cfg_path):
                            cfg_path = os.path.join(base_dir, cfg_path)
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        if isinstance(cfg, dict):
                            dv = cfg.get("data_vol", None)
                            if dv is not None:
                                try:
                                    data_vols.append(float(dv))
                                except Exception:
                                    pass
                            il = cfg.get("ingress_limit", None)
                            el = cfg.get("egress_limit", None)
                            if isinstance(il, dict):
                                ingress_candidates.append(il)
                            if isinstance(el, dict):
                                egress_candidates.append(el)
                    except Exception:
                        continue

                if data_vols:
                    data_vols_sorted = sorted(data_vols)
                    assumed_data_vol = float(data_vols_sorted[len(data_vols_sorted) // 2])

                if ingress_candidates:
                    # Use first; typically consistent
                    il0 = ingress_candidates[0]
                    for k in ingress_limit:
                        if k in il0:
                            try:
                                ingress_limit[k] = float(il0[k])
                            except Exception:
                                pass

                if egress_candidates:
                    el0 = egress_candidates[0]
                    for k in egress_limit:
                        if k in el0:
                            try:
                                egress_limit[k] = float(el0[k])
                            except Exception:
                                pass
            except Exception:
                pass

        code = f'''import math
import heapq
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import networkx as nx

NUM_VMS = {int(num_vms)}
ASSUMED_DATA_VOL = {float(assumed_data_vol)}
INGRESS_LIMIT = {json.dumps({k: float(v) for k, v in ingress_limit.items()})}
EGRESS_LIMIT = {json.dumps({k: float(v) for k, v in egress_limit.items()})}

INSTANCE_HOURLY_RATE = 0.54

class BroadCastTopology:
    def __init__(self, src: str, dsts: List[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {{dst: {{str(i): None for i in range(self.num_partitions)}} for dst in dsts}}

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: List[list]):
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        self.num_partitions = num_partitions


def _provider(node: str) -> str:
    if not node:
        return "aws"
    i = node.find(":")
    if i <= 0:
        return node.lower()
    return node[:i].lower()


def _build_adjacency(G: nx.DiGraph):
    adj = {{}}
    radj = {{}}
    nodes = list(G.nodes)
    for u in nodes:
        adj[u] = []
        radj[u] = []
    for u, nbrs in G.adj.items():
        au = adj.get(u)
        if au is None:
            au = []
            adj[u] = au
        for v, ed in nbrs.items():
            if v == u:
                continue
            try:
                cost = float(ed.get("cost", 0.0))
            except Exception:
                cost = 0.0
            try:
                thr = float(ed.get("throughput", 1.0))
            except Exception:
                thr = 1.0
            if thr <= 0:
                thr = 1e-9
            au.append((v, cost, thr))
            rv = radj.get(v)
            if rv is None:
                rv = []
                radj[v] = rv
            rv.append((u, cost, thr))
    return adj, radj


def _dijkstra(adj, src: str, weight_mode: str, theta: float):
    # weight_mode: "cost" or "hybrid"
    dist = {{}}
    parent = {{}}
    h = [(0.0, src)]
    dist[src] = 0.0
    parent[src] = None
    eps = 1e-12
    while h:
        d, u = heapq.heappop(h)
        if d != dist.get(u, None):
            continue
        for v, cost, thr in adj.get(u, ()):
            if weight_mode == "cost":
                w = cost
            else:
                w = cost + theta / (thr + eps)
            nd = d + w
            od = dist.get(v)
            if od is None or nd < od:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(h, (nd, v))
    return dist, parent


def _reconstruct_path_nodes(parent: Dict[str, Optional[str]], src: str, dst: str) -> Optional[List[str]]:
    if src == dst:
        return [src]
    if dst not in parent:
        return None
    path = []
    cur = dst
    seen = set()
    while cur != src:
        if cur is None or cur in seen:
            return None
        seen.add(cur)
        path.append(cur)
        cur = parent.get(cur)
        if cur is None:
            return None
    path.append(src)
    path.reverse()
    return path


def _nodes_to_edges(G: nx.DiGraph, nodes: List[str]) -> List[list]:
    if not nodes or len(nodes) == 1:
        return []
    edges = []
    for i in range(len(nodes) - 1):
        u = nodes[i]
        v = nodes[i + 1]
        if u == v:
            continue
        ed = G[u][v]
        edges.append([u, v, ed])
    return edges


def _edgeset_from_nodes(nodes: List[str]) -> List[Tuple[str, str]]:
    if not nodes or len(nodes) < 2:
        return []
    res = []
    for i in range(len(nodes) - 1):
        u = nodes[i]
        v = nodes[i + 1]
        if u != v:
            res.append((u, v))
    return res


def _approx_objective(G: nx.DiGraph,
                      hub_counts: Dict[str, int],
                      tree_edges_by_hub: Dict[str, List[Tuple[str, str]]],
                      s_partition: float) -> float:
    edge_counts = defaultdict(int)
    used_edges = set()
    for h, m in hub_counts.items():
        if m <= 0:
            continue
        for e in tree_edges_by_hub[h]:
            edge_counts[e] += m
            used_edges.add(e)

    if not used_edges:
        return float("inf")

    out_deg = defaultdict(int)
    in_deg = defaultdict(int)
    used_nodes = set()
    for u, v in used_edges:
        out_deg[u] += 1
        in_deg[v] += 1
        used_nodes.add(u)
        used_nodes.add(v)

    # Compute transfer time surrogate: max over edges of (|P_e| / f_e)
    t = 0.0
    egress_cost = 0.0
    for (u, v), cnt in edge_counts.items():
        if cnt <= 0:
            continue
        try:
            ed = G[u][v]
        except Exception:
            continue
        try:
            c = float(ed.get("cost", 0.0))
        except Exception:
            c = 0.0
        try:
            thr = float(ed.get("throughput", 1.0))
        except Exception:
            thr = 1.0
        if thr <= 0:
            thr = 1e-9

        pu = _provider(u)
        pv = _provider(v)
        el = float(EGRESS_LIMIT.get(pu, 8.0)) * float(NUM_VMS)
        il = float(INGRESS_LIMIT.get(pv, 16.0)) * float(NUM_VMS)

        od = out_deg.get(u, 1)
        idg = in_deg.get(v, 1)
        share_out = el / od if od > 0 else el
        share_in = il / idg if idg > 0 else il

        eff = min(thr, share_out, share_in)
        if eff <= 0:
            eff = 1e-9

        te = cnt / eff
        if te > t:
            t = te
        egress_cost += cnt * c

    # Convert surrogate into dollar estimate
    # Egress: sum(|P_e| * s_partition * c_e)
    # Instance: |V| * NUM_VMS * (r/3600) * t_seconds; t_seconds = t * s_partition * 8
    nodes_count = len(used_nodes)
    instance_coef = float(NUM_VMS) * float(INSTANCE_HOURLY_RATE) / 3600.0
    t_seconds = t * s_partition * 8.0
    inst_cost = nodes_count * instance_coef * t_seconds
    eg_cost = egress_cost * s_partition
    return eg_cost + inst_cost


def search_algorithm(src: str, dsts: List[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    num_partitions = int(num_partitions)
    bc = BroadCastTopology(src, dsts, num_partitions)

    if num_partitions <= 0:
        return bc
    if not dsts:
        return bc
    if src not in G:
        # Fallback: keep None paths (evaluator likely fails), but try to set empty
        for dst in dsts:
            for p in range(num_partitions):
                bc.set_dst_partition_paths(dst, p, [])
        return bc

    adj, radj = _build_adjacency(G)

    # Assumed partition size (GB) for objective calibration
    s_partition = float(ASSUMED_DATA_VOL) / float(num_partitions) if num_partitions > 0 else float(ASSUMED_DATA_VOL)

    # Hybrid weight parameter: scale throughput importance with partition size
    # (Large partition => more sensitive to throughput)
    theta = 0.05 * max(0.25, min(4.0, (s_partition / 30.0)))

    # Dijkstra from source once (hybrid)
    dist_src, par_src = _dijkstra(adj, src, "hybrid", theta)

    # Select candidate hubs using reverse distances (cost-only) from a subset of destinations
    dst_sample = list(dsts)
    if len(dst_sample) > 15:
        step = max(1, len(dst_sample) // 15)
        dst_sample = dst_sample[::step][:15]

    sum_cost_to_dsts = defaultdict(float)
    reach_count = defaultdict(int)

    for d in dst_sample:
        if d not in G:
            continue
        dist_rev, _ = _dijkstra(radj, d, "cost", theta=0.0)  # distances to d in original graph
        for n, dd in dist_rev.items():
            sum_cost_to_dsts[n] += dd
            reach_count[n] += 1

    nodes = list(G.nodes)
    hub_candidates = []
    for n in nodes:
        if n not in dist_src:
            continue
        rc = reach_count.get(n, 0)
        if rc <= 0:
            continue
        # Require reachability to most sampled destinations
        if rc < max(1, int(0.6 * len(dst_sample))):
            continue
        pu = _provider(n)
        cap = float(EGRESS_LIMIT.get(pu, 8.0)) * float(NUM_VMS)
        # lower is better
        sc = (sum_cost_to_dsts.get(n, 0.0) / max(1, rc)) / max(0.5, cap)
        hub_candidates.append((sc, n))

    hub_candidates.sort(key=lambda x: x[0])

    # Keep small set
    hubs = []
    hubs.append(src)
    seen = {src}
    max_hubs = 8
    for _, n in hub_candidates:
        if n in seen:
            continue
        hubs.append(n)
        seen.add(n)
        if len(hubs) >= max_hubs:
            break

    # Always include a few destinations as possible hubs (sometimes good in sparse graphs)
    for d in dsts[: min(3, len(dsts))]:
        if d in G and d not in seen and d in dist_src:
            hubs.append(d)
            seen.add(d)
        if len(hubs) >= max_hubs:
            break

    # Precompute per-hub: per-dst full path edges and hub tree edge set
    paths_by_hub_dst_edges: Dict[str, Dict[str, List[list]]] = {}
    tree_edges_by_hub: Dict[str, List[Tuple[str, str]]] = {}

    # Build src->hub node paths once using par_src
    src_to_hub_nodes: Dict[str, Optional[List[str]]] = {}
    for h in hubs:
        pn = _reconstruct_path_nodes(par_src, src, h)
        src_to_hub_nodes[h] = pn

    # Precompute hub->* dijkstra (hybrid) per hub
    for h in list(hubs):
        if h not in G:
            continue
        pn_src_h = src_to_hub_nodes.get(h)
        if pn_src_h is None:
            # unreachable hub from src
            continue

        dist_h, par_h = _dijkstra(adj, h, "hybrid", theta)
        per_dst_edges = {}
        tree_edges = set()

        # src->hub edges
        for e in _edgeset_from_nodes(pn_src_h):
            tree_edges.add(e)

        ok = True
        for d in dsts:
            if d not in G:
                ok = False
                break
            pn_h_d = _reconstruct_path_nodes(par_h, h, d)
            if pn_h_d is None:
                ok = False
                break

            # concatenate nodes: src->hub then hub->dst (skip duplicated hub)
            if len(pn_src_h) == 0:
                full_nodes = pn_h_d
            else:
                if pn_src_h[-1] == pn_h_d[0]:
                    full_nodes = pn_src_h + pn_h_d[1:]
                else:
                    full_nodes = pn_src_h + pn_h_d

            if not full_nodes or full_nodes[0] != src or full_nodes[-1] != d:
                ok = False
                break

            # edges for bc
            edge_list = _nodes_to_edges(G, full_nodes)
            per_dst_edges[d] = edge_list

            # edgeset for objective
            for e in _edgeset_from_nodes(full_nodes):
                tree_edges.add(e)

        if not ok:
            continue

        paths_by_hub_dst_edges[h] = per_dst_edges
        tree_edges_by_hub[h] = list(tree_edges)

    if src not in paths_by_hub_dst_edges:
        # Fallback: pure cost-based shortest paths per dst (no hub)
        for dst in dsts:
            try:
                path_nodes = nx.dijkstra_path(G, src, dst, weight="cost")
                edge_list = _nodes_to_edges(G, path_nodes)
            except Exception:
                edge_list = []
            for p in range(num_partitions):
                bc.set_dst_partition_paths(dst, p, edge_list)
        return bc

    # Reduce hubs to those with valid precomputations
    hubs = [h for h in hubs if h in paths_by_hub_dst_edges]
    if src not in hubs:
        hubs = [src] + hubs

    # Evaluate configurations: single hub, best pair, best triple
    best_obj = float("inf")
    best_counts = {src: num_partitions}

    def try_counts(counts: Dict[str, int]):
        nonlocal best_obj, best_counts
        # normalize counts to sum == num_partitions
        total = sum(max(0, int(v)) for v in counts.values())
        if total != num_partitions:
            return
        obj = _approx_objective(G, counts, tree_edges_by_hub, s_partition)
        if obj < best_obj:
            best_obj = obj
            best_counts = dict(counts)

    # Single hub
    for h in hubs:
        try_counts({h: num_partitions})

    # Pairs
    top_hubs = hubs[: min(len(hubs), 6)]
    if len(top_hubs) >= 2 and num_partitions >= 2:
        splits = sorted(set([num_partitions // 2, max(1, int(round(num_partitions * 0.33))), max(1, int(round(num_partitions * 0.67)))]))
        for i in range(len(top_hubs)):
            for j in range(i + 1, len(top_hubs)):
                h1 = top_hubs[i]
                h2 = top_hubs[j]
                for m1 in splits:
                    m1 = max(1, min(num_partitions - 1, int(m1)))
                    m2 = num_partitions - m1
                    try_counts({h1: m1, h2: m2})

    # Triples
    if len(top_hubs) >= 3 and num_partitions >= 3:
        m = num_partitions // 3
        base_splits = [(m, m, num_partitions - 2 * m),
                       (m, num_partitions - 2 * m, m),
                       (num_partitions - 2 * m, m, m)]
        for a in range(len(top_hubs)):
            for b in range(a + 1, len(top_hubs)):
                for c in range(b + 1, len(top_hubs)):
                    ha, hb, hc = top_hubs[a], top_hubs[b], top_hubs[c]
                    for x, y, z in base_splits:
                        if x <= 0 or y <= 0 or z <= 0:
                            continue
                        if x + y + z != num_partitions:
                            continue
                        try_counts({ha: x, hb: y, hc: z})

    # Assign partitions to hubs based on best_counts
    hub_list = []
    for h, m in sorted(best_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if m > 0:
            hub_list.extend([h] * int(m))
    if len(hub_list) != num_partitions:
        hub_list = [src] * num_partitions

    # Build topology
    for dst in dsts:
        for p in range(num_partitions):
            h = hub_list[p]
            if h not in paths_by_hub_dst_edges:
                h = src
            edge_list = paths_by_hub_dst_edges[h].get(dst)
            if edge_list is None:
                # fallback to src hub path
                edge_list = paths_by_hub_dst_edges[src].get(dst, [])
            bc.set_dst_partition_paths(dst, p, edge_list)

    return bc
'''
        return {"code": code}