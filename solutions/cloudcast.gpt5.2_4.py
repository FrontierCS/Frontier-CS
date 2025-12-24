import json
from typing import Any, Dict


ALGO_CODE = r'''import math
import heapq
import networkx as nx


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


def _provider(node: str) -> str:
    if not isinstance(node, str):
        return "aws"
    p = node.split(":", 1)[0].strip().lower()
    if p.startswith("az"):
        return "azure"
    if p in ("aws", "gcp", "azure"):
        return p
    return p


def _get_limits(G: nx.DiGraph):
    ingress_default = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
    egress_default = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}

    ingress = G.graph.get("ingress_limit", None)
    egress = G.graph.get("egress_limit", None)
    if isinstance(ingress, dict):
        ing = {k.lower(): float(v) for k, v in ingress.items()}
        for k, v in ingress_default.items():
            ing.setdefault(k, v)
        ingress = ing
    else:
        ingress = ingress_default

    if isinstance(egress, dict):
        eg = {k.lower(): float(v) for k, v in egress.items()}
        for k, v in egress_default.items():
            eg.setdefault(k, v)
        egress = eg
    else:
        egress = egress_default

    num_vms = G.graph.get("num_vms", None)
    try:
        num_vms = int(num_vms) if num_vms is not None else 2
    except Exception:
        num_vms = 2

    return ingress, egress, num_vms


def _edge_weight(cost: float, thr: float, prov_u: str, mode: int, egress_lim: dict) -> float:
    # mode 0: cost
    # mode 1: cost + alpha/thr
    # mode 2: hop-ish
    # mode 3: cost + alpha/thr + beta*(1/egress_limit(provider(u)))
    if thr <= 1e-12:
        thr = 1e-12
    if cost < 0.0:
        cost = 0.0

    if mode == 0:
        return cost
    if mode == 1:
        return cost + (0.08 / thr)
    if mode == 2:
        return 1.0 + 0.03 * cost
    # mode == 3
    el = float(egress_lim.get(prov_u, 10.0))
    return cost + (0.05 / thr) + (0.01 / max(el, 1e-12))


def _dijkstra_single_source(adj, src: int, n: int, mode: int, prov_idx, egress_lim):
    INF = float("inf")
    dist = [INF] * n
    pred = [-1] * n
    dist[src] = 0.0
    heap = [(0.0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist[u]:
            continue
        pu = prov_idx[u]
        for v, cost, thr in adj[u]:
            w = _edge_weight(cost, thr, pu, mode, egress_lim)
            nd = d + w
            if nd + 1e-12 < dist[v]:
                dist[v] = nd
                pred[v] = u
                heapq.heappush(heap, (nd, v))
            elif abs(nd - dist[v]) <= 1e-12:
                # deterministic tie-breaker: smaller predecessor index
                if pred[v] == -1 or u < pred[v]:
                    pred[v] = u
    return dist, pred


def _dijkstra_multisource(adj, sources, n: int, mode: int, prov_idx, egress_lim):
    INF = float("inf")
    dist = [INF] * n
    pred = [-1] * n
    root = [-1] * n
    heap = []
    for s in sources:
        dist[s] = 0.0
        pred[s] = -1
        root[s] = s
        heap.append((0.0, s))
    heapq.heapify(heap)
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist[u]:
            continue
        pu = prov_idx[u]
        ru = root[u]
        for v, cost, thr in adj[u]:
            w = _edge_weight(cost, thr, pu, mode, egress_lim)
            nd = d + w
            if nd + 1e-12 < dist[v]:
                dist[v] = nd
                pred[v] = u
                root[v] = ru
                heapq.heappush(heap, (nd, v))
            elif abs(nd - dist[v]) <= 1e-12:
                if pred[v] == -1 or u < pred[v]:
                    pred[v] = u
                    root[v] = ru
    return dist, pred, root


def _reconstruct_path(pred, src: int, dst: int):
    # from src to dst using pred pointers pointing to predecessor
    path = []
    cur = dst
    seen = set()
    while cur != -1 and cur not in seen:
        seen.add(cur)
        path.append(cur)
        if cur == src:
            break
        cur = pred[cur]
    if not path or path[-1] != src:
        return None
    path.reverse()
    return path


class _Tree:
    __slots__ = ("name", "dst_paths", "edges", "nodes")

    def __init__(self, name: str, dst_paths: dict[int, list[int]], src_idx: int):
        self.name = name
        self.dst_paths = dst_paths
        edges = set()
        nodes = set([src_idx])
        for p in dst_paths.values():
            if not p or len(p) < 2:
                continue
            for i in range(len(p) - 1):
                u = p[i]
                v = p[i + 1]
                if u != v:
                    edges.add((u, v))
                    nodes.add(u)
                    nodes.add(v)
        self.edges = edges
        self.nodes = nodes


def _build_spt(name: str, adj, n: int, src_idx: int, dst_idxs: list[int], mode: int, prov_idx, egress_lim):
    dist, pred = _dijkstra_single_source(adj, src_idx, n, mode, prov_idx, egress_lim)
    dst_paths = {}
    for d in dst_idxs:
        if dist[d] == float("inf"):
            return None
        p = _reconstruct_path(pred, src_idx, d)
        if not p:
            return None
        dst_paths[d] = p
    return _Tree(name, dst_paths, src_idx)


def _build_sph(name: str, adj, n: int, src_idx: int, dst_idxs: list[int], mode: int, prov_idx, egress_lim):
    remaining = set(dst_idxs)
    tree_nodes = set([src_idx])
    path_from_src = {src_idx: [src_idx]}
    dst_paths = {}

    while remaining:
        sources = list(tree_nodes)
        dist, pred, root = _dijkstra_multisource(adj, sources, n, mode, prov_idx, egress_lim)

        best_d = None
        best_dist = float("inf")
        for d in remaining:
            dd = dist[d]
            if dd < best_dist:
                best_dist = dd
                best_d = d

        if best_d is None or best_dist == float("inf"):
            return None

        attach = root[best_d]
        # reconstruct attach -> best_d using pred pointers (stops at a source)
        tail = []
        cur = best_d
        seen = set()
        while cur != -1 and cur not in seen:
            seen.add(cur)
            tail.append(cur)
            if cur == attach:
                break
            cur = pred[cur]
        if not tail or tail[-1] != attach:
            return None
        tail.reverse()

        prefix = path_from_src.get(attach)
        if not prefix:
            # Shouldn't happen; attach must already be in tree
            prefix = [src_idx, attach] if src_idx != attach else [src_idx]

        full = prefix + tail[1:]
        dst_paths[best_d] = full

        # Add nodes/paths along the newly added segment (using the full path edges)
        for i in range(len(full) - 1):
            u = full[i]
            v = full[i + 1]
            if v not in path_from_src:
                path_from_src[v] = path_from_src[u] + [v]
            tree_nodes.add(u)
            tree_nodes.add(v)

        remaining.remove(best_d)

    return _Tree(name, dst_paths, src_idx)


def _eval_mix(trees: list[_Tree], counts: list[int], n: int, src_idx: int, prov_idx, ingress_lim, egress_lim, num_vms: int, edge_cost, edge_thr):
    # union edges among used trees
    used = [i for i, c in enumerate(counts) if c > 0]
    if not used:
        return float("inf")

    union_edges = set()
    for i in used:
        union_edges |= trees[i].edges

    if not union_edges:
        return float("inf")

    n_out = {}
    n_in = {}
    nodes = set([src_idx])
    for (u, v) in union_edges:
        n_out[u] = n_out.get(u, 0) + 1
        n_in[v] = n_in.get(v, 0) + 1
        nodes.add(u)
        nodes.add(v)

    # partition counts per edge
    count_e = {}
    for i in used:
        m = counts[i]
        if m <= 0:
            continue
        for e in trees[i].edges:
            count_e[e] = count_e.get(e, 0) + m

    # compute max transfer time over edges
    t_transfer = 0.0
    egress_cost = 0.0
    for (u, v), cpart in count_e.items():
        if cpart <= 0:
            continue
        cost = edge_cost.get((u, v), 1.0)
        thr = edge_thr.get((u, v), 1e-12)
        # node enforced per-edge throughput
        pu = prov_idx[u]
        pv = prov_idx[v]
        out_lim = float(egress_lim.get(pu, 10.0)) * float(num_vms)
        in_lim = float(ingress_lim.get(pv, 10.0)) * float(num_vms)
        if out_lim > 0 and n_out.get(u, 1) > 0:
            thr = min(thr, out_lim / float(n_out[u]))
        if in_lim > 0 and n_in.get(v, 1) > 0:
            thr = min(thr, in_lim / float(n_in[v]))
        thr = max(thr, 1e-12)

        egress_cost += float(cpart) * float(cost)

        # s_partition normalized to 1 GB => 8 Gb
        t = (float(cpart) * 8.0) / thr
        if t > t_transfer:
            t_transfer = t

    node_count = len(nodes)

    # instance cost: |V| * n_vm * r/3600 * t_transfer
    r_instance = 0.54
    instance_cost = float(node_count) * float(num_vms) * (r_instance / 3600.0) * float(t_transfer)

    return egress_cost + instance_cost


def _compositions_positive(total: int, k: int):
    # yield k-tuples of positive ints summing to total
    if k == 1:
        yield (total,)
        return
    # recursive
    def rec(remaining, parts_left, prefix):
        if parts_left == 1:
            yield prefix + (remaining,)
            return
        # each part at least 1
        max_first = remaining - (parts_left - 1)
        for x in range(1, max_first + 1):
            yield from rec(remaining - x, parts_left - 1, prefix + (x,))
    yield from rec(total, k, ())


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    num_partitions = int(num_partitions)
    bc = BroadCastTopology(src, dsts, num_partitions)

    if num_partitions <= 0 or not dsts:
        return bc

    nodes = list(G.nodes())
    if src not in G:
        # impossible; return empty paths (will fail evaluator), but keep deterministic
        return bc

    node_to_idx = {node: i for i, node in enumerate(nodes)}
    idx_to_node = nodes
    n = len(nodes)

    src_idx = node_to_idx[src]
    dst_idxs = []
    for d in dsts:
        if d in node_to_idx:
            dst_idxs.append(node_to_idx[d])
        else:
            # missing destination node; return trivial (will likely fail), but keep deterministic
            return bc

    prov_idx = [_provider(node) for node in idx_to_node]
    ingress_lim, egress_lim, num_vms = _get_limits(G)

    # adjacency list with cost and throughput
    adj = [[] for _ in range(n)]
    edge_cost = {}
    edge_thr = {}
    for u in G.nodes():
        ui = node_to_idx[u]
        for v, data in G[u].items():
            if u == v:
                continue
            vi = node_to_idx[v]
            cost = float(data.get("cost", 1.0))
            thr = float(data.get("throughput", 1e-12))
            if thr <= 0:
                thr = 1e-12
            adj[ui].append((vi, cost, thr))
            edge_cost[(ui, vi)] = cost
            edge_thr[(ui, vi)] = thr

    # Candidate generation
    candidates = []
    seen = set()

    def add_tree(t: _Tree):
        if t is None:
            return
        sig = tuple(sorted(t.edges))
        if sig in seen:
            return
        seen.add(sig)
        candidates.append(t)

    modes = [
        (0, "cost"),
        (1, "mix"),
        (3, "egress"),
        (2, "hop"),
    ]

    for mode, mname in modes:
        add_tree(_build_spt(f"spt_{mname}", adj, n, src_idx, dst_idxs, mode, prov_idx, egress_lim))
        add_tree(_build_sph(f"sph_{mname}", adj, n, src_idx, dst_idxs, mode, prov_idx, egress_lim))

    # fallback: per-destination shortest path union (networkx), in case custom trees fail
    if not candidates:
        for d in dsts:
            try:
                pn = nx.dijkstra_path(G, src, d, weight="cost")
            except Exception:
                pn = None
            if not pn:
                return bc
            for pid in range(num_partitions):
                edges = []
                for i in range(len(pn) - 1):
                    u, v = pn[i], pn[i + 1]
                    edges.append([u, v, G[u][v]])
                bc.set_dst_partition_paths(d, pid, edges)
        return bc

    # Score single candidates to pick top M
    single_scores = []
    for i, t in enumerate(candidates):
        total = _eval_mix([t], [num_partitions], n, src_idx, prov_idx, ingress_lim, egress_lim, num_vms, edge_cost, edge_thr)
        single_scores.append((total, i))
    single_scores.sort()
    M = min(5, len(single_scores))
    top_idx = [i for _, i in single_scores[:M]]
    top_trees = [candidates[i] for i in top_idx]

    best_total = float("inf")
    best_counts = None
    best_used_trees = None

    # size 1..3 mixtures among top trees
    # size 1
    for i, t in enumerate(top_trees):
        total = _eval_mix([t], [num_partitions], n, src_idx, prov_idx, ingress_lim, egress_lim, num_vms, edge_cost, edge_thr)
        if total < best_total:
            best_total = total
            best_counts = [num_partitions]
            best_used_trees = [t]

    # size 2 and 3
    L = len(top_trees)
    # size 2
    if num_partitions >= 2 and L >= 2:
        for a in range(L):
            for b in range(a + 1, L):
                t1, t2 = top_trees[a], top_trees[b]
                for x in range(1, num_partitions):
                    counts = [x, num_partitions - x]
                    total = _eval_mix([t1, t2], counts, n, src_idx, prov_idx, ingress_lim, egress_lim, num_vms, edge_cost, edge_thr)
                    if total < best_total:
                        best_total = total
                        best_counts = counts
                        best_used_trees = [t1, t2]

    # size 3
    if num_partitions >= 3 and L >= 3:
        for a in range(L):
            for b in range(a + 1, L):
                for c in range(b + 1, L):
                    t1, t2, t3 = top_trees[a], top_trees[b], top_trees[c]
                    for counts in _compositions_positive(num_partitions, 3):
                        counts = list(counts)
                        total = _eval_mix([t1, t2, t3], counts, n, src_idx, prov_idx, ingress_lim, egress_lim, num_vms, edge_cost, edge_thr)
                        if total < best_total:
                            best_total = total
                            best_counts = counts
                            best_used_trees = [t1, t2, t3]

    if best_used_trees is None:
        # should not happen
        best_used_trees = [top_trees[0]]
        best_counts = [num_partitions]

    # Assign partitions to chosen trees (partition ids are interchangeable)
    part_to_tree = []
    for ti, c in enumerate(best_counts):
        part_to_tree.extend([ti] * int(c))
    # ensure length
    if len(part_to_tree) < num_partitions:
        part_to_tree.extend([0] * (num_partitions - len(part_to_tree)))
    elif len(part_to_tree) > num_partitions:
        part_to_tree = part_to_tree[:num_partitions]

    # Prebuild per-tree per-dst edge lists (as required by evaluator)
    tree_dst_edges = []
    for t in best_used_trees:
        per_dst = {}
        for dname, didx in zip(dsts, dst_idxs):
            pidx = t.dst_paths.get(didx)
            if not pidx or len(pidx) < 2:
                # fallback to dijkstra for this dst
                try:
                    pn = nx.dijkstra_path(G, src, dname, weight="cost")
                    pidx = [node_to_idx[x] for x in pn]
                except Exception:
                    pidx = None
            if not pidx:
                return bc
            edges = []
            ok = True
            for i in range(len(pidx) - 1):
                u = idx_to_node[pidx[i]]
                v = idx_to_node[pidx[i + 1]]
                if u == v or not G.has_edge(u, v):
                    ok = False
                    break
                edges.append([u, v, G[u][v]])
            if not ok:
                # fallback to networkx
                try:
                    pn = nx.dijkstra_path(G, src, dname, weight="cost")
                    edges = []
                    for i in range(len(pn) - 1):
                        u, v = pn[i], pn[i + 1]
                        edges.append([u, v, G[u][v]])
                except Exception:
                    return bc
            per_dst[dname] = edges
        tree_dst_edges.append(per_dst)

    for pid in range(num_partitions):
        ti = part_to_tree[pid]
        per_dst = tree_dst_edges[ti]
        for d in dsts:
            bc.set_dst_partition_paths(d, pid, per_dst[d])

    return bc
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": ALGO_CODE}
