import json
import os
from typing import Dict, List, Tuple, Set, Optional

ALGO_TEMPLATE = r'''
import math
import networkx as nx

NUM_VMS = __NUM_VMS__
INGRESS_LIMIT = __INGRESS_LIMIT__
EGRESS_LIMIT = __EGRESS_LIMIT__

_INSTANCE_RATE_PER_HOUR = 0.54
_INST_COEFF = (NUM_VMS * _INSTANCE_RATE_PER_HOUR / 3600.0) * 8.0  # $/(GB) multiplier for (|V| * max(|P_e|/f_e))


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


def _provider(node: str) -> str:
    if not node:
        return ""
    i = node.find(":")
    if i <= 0:
        return node.lower()
    return node[:i].lower()


def _get_lim(d: dict, k: str, default: float) -> float:
    try:
        v = d.get(k, default)
        v = float(v)
        if v > 0:
            return v
    except Exception:
        pass
    return float(default)


def _tree_build_arborescence(src: str, dsts: list, G: nx.DiGraph, weight_attr: str) -> Tuple[dict, Set[Tuple[str, str]], Set[str], float]:
    tree_nodes = set([src])
    parent = {}
    edges = set()

    remaining = set(dsts)
    if src in remaining:
        remaining.remove(src)
    remaining = {d for d in remaining if d not in tree_nodes}

    while remaining:
        try:
            dist, paths = nx.multi_source_dijkstra(G, tree_nodes, weight=weight_attr)
        except Exception:
            dist = {}
            paths = {}

        best_dst = None
        best_dist = float("inf")
        for d in remaining:
            dd = dist.get(d, None)
            if dd is not None and dd < best_dist:
                best_dist = dd
                best_dst = d

        if best_dst is None:
            break

        path_nodes = paths.get(best_dst)
        if not path_nodes or len(path_nodes) < 2:
            remaining.remove(best_dst)
            continue

        last_in_tree_idx = 0
        for i, n in enumerate(path_nodes):
            if n in tree_nodes:
                last_in_tree_idx = i
        sub = path_nodes[last_in_tree_idx:]

        # Add only new nodes in a parent-tree manner
        a = sub[0]
        for b in sub[1:]:
            if b in tree_nodes:
                a = b
                continue
            if a == b:
                a = b
                continue
            if not G.has_edge(a, b):
                a = b
                continue
            parent[b] = a
            edges.add((a, b))
            tree_nodes.add(b)
            a = b

        # Some other destinations might have been added as intermediate nodes
        remaining = {d for d in remaining if d not in tree_nodes}

    # Fallback: connect any remaining destination directly from src using Dijkstra
    for d in list(remaining):
        if d == src:
            remaining.discard(d)
            continue
        if d in tree_nodes:
            remaining.discard(d)
            continue
        try:
            pn = nx.dijkstra_path(G, src, d, weight=weight_attr)
        except Exception:
            pn = None
        if not pn or len(pn) < 2:
            continue
        last_in_tree_idx = 0
        for i, n in enumerate(pn):
            if n in tree_nodes:
                last_in_tree_idx = i
        sub = pn[last_in_tree_idx:]
        a = sub[0]
        for b in sub[1:]:
            if b in tree_nodes:
                a = b
                continue
            if a == b:
                a = b
                continue
            if not G.has_edge(a, b):
                a = b
                continue
            parent[b] = a
            edges.add((a, b))
            tree_nodes.add(b)
            a = b

    nodes = set(tree_nodes)
    cost_sum = 0.0
    for u, v in edges:
        try:
            cost_sum += float(G[u][v].get("cost", 0.0))
        except Exception:
            pass
    return parent, edges, nodes, cost_sum


def _compute_degrees(edges: Set[Tuple[str, str]]) -> Tuple[dict, dict]:
    outdeg = {}
    indeg = {}
    for u, v in edges:
        outdeg[u] = outdeg.get(u, 0) + 1
        indeg[v] = indeg.get(v, 0) + 1
    return outdeg, indeg


def _effective_throughput(u: str, v: str, edata: dict, outdeg: dict, indeg: dict) -> float:
    try:
        tp = float(edata.get("throughput", 0.0))
    except Exception:
        tp = 0.0
    if tp <= 0:
        tp = 1e-9

    pu = _provider(u)
    pv = _provider(v)
    out_d = outdeg.get(u, 0)
    in_d = indeg.get(v, 0)

    out_share = float("inf")
    in_share = float("inf")

    if out_d > 0:
        out_lim = _get_lim(EGRESS_LIMIT, pu, 1e9) * float(NUM_VMS)
        out_share = out_lim / float(out_d)
    if in_d > 0:
        in_lim = _get_lim(INGRESS_LIMIT, pv, 1e9) * float(NUM_VMS)
        in_share = in_lim / float(in_d)

    f = tp
    if out_share < f:
        f = out_share
    if in_share < f:
        f = in_share
    if f <= 0:
        return 1e-9
    return f


def _max_ratio(edges: Set[Tuple[str, str]], G: nx.DiGraph, loads: dict, outdeg: dict, indeg: dict) -> float:
    mr = 0.0
    for (u, v) in edges:
        l = loads.get((u, v), 0)
        if l <= 0:
            continue
        edata = G[u][v]
        f = _effective_throughput(u, v, edata, outdeg, indeg)
        r = float(l) / float(f)
        if r > mr:
            mr = r
    return mr


def _node_count_from_edges(edges: Set[Tuple[str, str]], src: str) -> int:
    nodes = set([src])
    for u, v in edges:
        nodes.add(u)
        nodes.add(v)
    return len(nodes)


def _build_paths_from_parent(src: str, dsts: list, parent: dict) -> dict:
    paths = {}
    for dst in dsts:
        if dst == src:
            paths[dst] = []
            continue
        cur = dst
        rev = []
        seen = set()
        ok = True
        while cur != src:
            if cur in seen:
                ok = False
                break
            seen.add(cur)
            p = parent.get(cur)
            if p is None:
                ok = False
                break
            rev.append((p, cur))
            cur = p
        if not ok:
            paths[dst] = None
        else:
            rev.reverse()
            paths[dst] = rev
    return paths


def _prepare_base_weights(G: nx.DiGraph) -> Tuple[float, float]:
    total_c = 0.0
    cnt_c = 0
    total_t = 0.0
    cnt_t = 0
    for _, _, d in G.edges(data=True):
        try:
            c = float(d.get("cost", 0.0))
            if c >= 0:
                total_c += c
                cnt_c += 1
        except Exception:
            pass
        try:
            t = float(d.get("throughput", 0.0))
            if t > 0:
                total_t += t
                cnt_t += 1
        except Exception:
            pass
    avg_c = total_c / cnt_c if cnt_c else 0.05
    avg_t = total_t / cnt_t if cnt_t else 10.0
    if avg_c <= 0:
        avg_c = 0.05
    if avg_t <= 0:
        avg_t = 10.0
    return avg_c, avg_t


def search_algorithm(src: str, dsts: list, G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    num_partitions = int(num_partitions)
    bc = BroadCastTopology(src, dsts, num_partitions)

    if num_partitions <= 0:
        return bc

    # Precompute base weights
    avg_cost, avg_tp = _prepare_base_weights(G)

    # Base: cost-only
    for u, v, d in G.edges(data=True):
        try:
            d["w0"] = float(d.get("cost", 0.0))
        except Exception:
            d["w0"] = 0.0

    parent0, edges0, nodes0, cost0 = _tree_build_arborescence(src, dsts, G, "w0")
    paths0 = _build_paths_from_parent(src, dsts, parent0)

    # If base tree failed for any destination, fall back to per-destination shortest path (cost)
    if any(paths0.get(d) is None for d in dsts):
        for dst in dsts:
            if dst == src:
                paths0[dst] = []
                continue
            try:
                pn = nx.dijkstra_path(G, src, dst, weight="w0")
            except Exception:
                pn = None
            if not pn or len(pn) < 2:
                paths0[dst] = []
                continue
            pe = []
            for i in range(len(pn) - 1):
                pe.append((pn[i], pn[i + 1]))
                edges0.add((pn[i], pn[i + 1]))
                nodes0.add(pn[i])
                nodes0.add(pn[i + 1])
            paths0[dst] = pe
        cost0 = 0.0
        for u, v in edges0:
            try:
                cost0 += float(G[u][v].get("cost", 0.0))
            except Exception:
                pass

    # Identify bottlenecks in the base tree using an approximate effective throughput
    out0, in0 = _compute_degrees(edges0)
    ratios0 = []
    for (u, v) in edges0:
        edata = G[u][v]
        f = _effective_throughput(u, v, edata, out0, in0)
        ratios0.append(((float(num_partitions) / float(f)), (u, v)))
    ratios0.sort(reverse=True, key=lambda x: x[0])
    top_m = min(max(1, len(ratios0) // 4), 12)
    bottlenecks = set([e for _, e in ratios0[:top_m]])

    # Alternative: bias away from bottlenecks and mildly toward high throughput
    eps = 1e-9
    lam = avg_cost * avg_tp * 0.25
    if lam < avg_cost * 0.02:
        lam = avg_cost * 0.02
    if lam > 0.3:
        lam = 0.3
    penalty_bn = max(0.02, avg_cost * 2.0)

    for u, v, d in G.edges(data=True):
        try:
            c = float(d.get("cost", 0.0))
        except Exception:
            c = 0.0
        try:
            t = float(d.get("throughput", 0.0))
        except Exception:
            t = 0.0
        if t <= 0:
            t = 1e-9
        w = c + (lam / (t + eps))
        if (u, v) in bottlenecks:
            w += penalty_bn
        d["w1"] = w

    parent1, edges1, nodes1, cost1 = _tree_build_arborescence(src, dsts, G, "w1")
    paths1 = _build_paths_from_parent(src, dsts, parent1)

    # If alternative tree is invalid, disable it
    if any(paths1.get(d) is None for d in dsts):
        edges1 = set()
        nodes1 = set([src])
        cost1 = float("inf")
        paths1 = {d: None for d in dsts}

    # If tree1 isn't usable or is identical, just use tree0 for all partitions
    if not edges1 or edges1 == edges0 or not math.isfinite(cost1):
        for dst in dsts:
            pe = paths0.get(dst) or []
            out = []
            for (u, v) in pe:
                out.append([u, v, G[u][v]])
            for p in range(num_partitions):
                bc.set_dst_partition_paths(dst, p, out)
        return bc

    # Evaluate splitting partitions between the two trees
    best_x = 0
    best_obj = float("inf")
    n = num_partitions

    for x in range(0, n + 1):
        use0 = (n - x) > 0
        use1 = x > 0

        if use0 and use1:
            union_edges = edges0 | edges1
        elif use0:
            union_edges = edges0
        else:
            union_edges = edges1

        outdeg, indeg = _compute_degrees(union_edges)

        loads = {}
        if use0:
            for e in edges0:
                loads[e] = loads.get(e, 0) + (n - x)
        if use1:
            for e in edges1:
                loads[e] = loads.get(e, 0) + x

        mr = _max_ratio(union_edges, G, loads, outdeg, indeg)
        node_cnt = _node_count_from_edges(union_edges, src)

        # Egress cost per GB: partitions * sum(edge cost) for each tree
        egress = 0.0
        if use0:
            egress += float(n - x) * float(cost0)
        if use1:
            egress += float(x) * float(cost1)

        inst = _INST_COEFF * float(node_cnt) * float(mr)
        obj = egress + inst

        if obj < best_obj:
            best_obj = obj
            best_x = x

    # Assign first best_x partitions to tree1, rest to tree0
    for dst in dsts:
        pe0 = paths0.get(dst) or []
        pe1 = paths1.get(dst) or pe0

        out0_list = []
        for (u, v) in pe0:
            out0_list.append([u, v, G[u][v]])

        out1_list = []
        for (u, v) in pe1:
            out1_list.append([u, v, G[u][v]])

        for p in range(num_partitions):
            if p < best_x:
                bc.set_dst_partition_paths(dst, p, out1_list)
            else:
                bc.set_dst_partition_paths(dst, p, out0_list)

    return bc
'''


def _render_algorithm_code(num_vms: int, ingress_limit: Dict, egress_limit: Dict) -> str:
    code = ALGO_TEMPLATE
    code = code.replace("__NUM_VMS__", str(int(num_vms)))
    code = code.replace("__INGRESS_LIMIT__", repr({k.lower(): float(v) for k, v in (ingress_limit or {}).items()}))
    code = code.replace("__EGRESS_LIMIT__", repr({k.lower(): float(v) for k, v in (egress_limit or {}).items()}))
    return code


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_spec_params(spec_path: Optional[str]):
    default_ingress = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
    default_egress = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}
    num_vms = 2

    if not spec_path or not os.path.exists(spec_path):
        return num_vms, default_ingress, default_egress

    try:
        spec = _read_json(spec_path)
        if isinstance(spec, dict):
            nv = spec.get("num_vms", None)
            if nv is not None:
                try:
                    num_vms = int(nv)
                except Exception:
                    pass

            cfgs = spec.get("config_files", [])
            base_dir = os.path.dirname(os.path.abspath(spec_path))
            ingress = dict(default_ingress)
            egress = dict(default_egress)

            if isinstance(cfgs, list):
                for cf in cfgs:
                    if not isinstance(cf, str):
                        continue
                    cf_path = cf
                    if not os.path.isabs(cf_path):
                        cf_path = os.path.join(base_dir, cf_path)
                    if not os.path.exists(cf_path):
                        continue
                    try:
                        cfg = _read_json(cf_path)
                    except Exception:
                        continue
                    if isinstance(cfg, dict):
                        il = cfg.get("ingress_limit", None)
                        el = cfg.get("egress_limit", None)
                        if isinstance(il, dict):
                            for k, v in il.items():
                                try:
                                    ingress[str(k).lower()] = float(v)
                                except Exception:
                                    pass
                        if isinstance(el, dict):
                            for k, v in el.items():
                                try:
                                    egress[str(k).lower()] = float(v)
                                except Exception:
                                    pass
            return num_vms, ingress, egress
    except Exception:
        pass

    return num_vms, default_ingress, default_egress


# Provide module-level definitions as a fallback (in case the harness imports them directly).
# These use default parameters (num_vms=2, standard per-provider limits).
_default_code = _render_algorithm_code(
    2,
    {"aws": 10.0, "gcp": 16.0, "azure": 16.0},
    {"aws": 5.0, "gcp": 7.0, "azure": 16.0},
)
_exec_ns = {}
exec(_default_code, _exec_ns)
BroadCastTopology = _exec_ns["BroadCastTopology"]
search_algorithm = _exec_ns["search_algorithm"]


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms, ingress, egress = _load_spec_params(spec_path)
        code = _render_algorithm_code(num_vms, ingress, egress)
        return {"code": code}
