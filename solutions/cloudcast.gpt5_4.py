import json
import os
import networkx as nx

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        ingress_limit_default = {"aws": 10, "gcp": 16, "azure": 16}
        egress_limit_default = {"aws": 5, "gcp": 7, "azure": 16}
        ingress_limits = ingress_limit_default.copy()
        egress_limits = egress_limit_default.copy()

        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, "r") as f:
                    spec = json.load(f)
                if isinstance(spec, dict):
                    if "num_vms" in spec and isinstance(spec["num_vms"], int) and spec["num_vms"] > 0:
                        num_vms = spec["num_vms"]
                    cfg_files = spec.get("config_files", [])
                    if cfg_files and isinstance(cfg_files, list):
                        first_cfg = cfg_files[0]
                        if os.path.exists(first_cfg):
                            with open(first_cfg, "r") as cf:
                                cfg = json.load(cf)
                            if isinstance(cfg, dict):
                                ing = cfg.get("ingress_limit", {})
                                egr = cfg.get("egress_limit", {})
                                for k in ingress_limit_default:
                                    if isinstance(ing.get(k), (int, float)) and ing[k] > 0:
                                        ingress_limits[k] = float(ing[k])
                                    if isinstance(egr.get(k), (int, float)) and egr[k] > 0:
                                        egress_limits[k] = float(egr[k])
            except Exception:
                pass

        code = f'''
import networkx as nx

N_VMS = {num_vms}
INGRESS_LIMITS = {{"aws": {ingress_limits["aws"]} * N_VMS, "gcp": {ingress_limits["gcp"]} * N_VMS, "azure": {ingress_limits["azure"]} * N_VMS}}
EGRESS_LIMITS = {{"aws": {egress_limits["aws"]} * N_VMS, "gcp": {egress_limits["gcp"]} * N_VMS, "azure": {egress_limits["azure"]} * N_VMS}}

def _provider_of(node: str) -> str:
    try:
        if ":" in node:
            return node.split(":", 1)[0].strip().lower()
        return node.split("-", 1)[0].strip().lower()
    except Exception:
        return "aws"

def _edge_key(u, v):
    return (u, v)

def _safe_cost(val):
    try:
        x = float(val)
        if x >= 0:
            return x
        return 0.0
    except Exception:
        return 0.0

def _safe_thr(val):
    try:
        x = float(val)
        if x > 0:
            return x
        return 1e-6
    except Exception:
        return 1e-6

def _edge_cost(G, u, v):
    data = G[u][v]
    return _safe_cost(data.get("cost", 0.0))

def _edge_thr(G, u, v):
    data = G[u][v]
    return _safe_thr(data.get("throughput", 1e6))

def _compute_path_cost(G, path_nodes):
    if len(path_nodes) < 2:
        return 0.0
    c = 0.0
    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i+1]
        if G.has_edge(u, v):
            c += _edge_cost(G, u, v)
        else:
            c += 0.0
    return c

def _path_to_edges(G, path_nodes):
    edges = []
    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i+1]
        edges.append([u, v, G[u][v]])
    return edges

def _get_k_shortest_paths(G, src, dst, K):
    # Create or update a lightweight weight attribute for K-shortest computation.
    # cost dominates; small penalty for low throughput to avoid very slow links.
    gamma = 1e-4
    for u, v in G.edges():
        d = G[u][v]
        c = _safe_cost(d.get("cost", 0.0))
        t = _safe_thr(d.get("throughput", 1e6))
        d["__w"] = c + gamma * (1.0 / max(t, 1e-9))

    paths = []
    try:
        gen = nx.shortest_simple_paths(G, src, dst, weight="__w")
        for idx, p in enumerate(gen):
            if idx >= K:
                break
            paths.append(p)
    except Exception:
        try:
            p = nx.dijkstra_path(G, src, dst, weight="__w")
            paths.append(p)
        except Exception:
            try:
                p = nx.shortest_path(G, src, dst)
                paths.append(p)
            except Exception:
                pass
    # Clean temporary weight if desired (not necessary)
    return paths

def _predicted_max_ratio_after_add(G, edge_counts, active_edges, out_active_counts, in_active_counts, path_nodes):
    # Approximate per-edge actual throughput considering node ingress/egress equal split among active edges.
    # Build predicted node active counts after adding edges from path.
    pred_out_counts = dict(out_active_counts)
    pred_in_counts = dict(in_active_counts)

    # Determine provider node mapping for limits
    # Precomputed via _provider_of when needed

    # Edges on the path
    path_edges = []
    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i+1]
        path_edges.append((u, v))
        ek = (u, v)
        if ek not in active_edges:
            pred_out_counts[u] = pred_out_counts.get(u, 0) + 1
            pred_in_counts[v] = pred_in_counts.get(v, 0) + 1

    # Candidate edges to evaluate: existing active edges union new path edges
    candidate_edges = set(active_edges)
    candidate_edges.update(path_edges)

    max_ratio = 0.0
    for (u, v) in candidate_edges:
        prov_u = _provider_of(u)
        prov_v = _provider_of(v)
        outn = max(1, pred_out_counts.get(u, 0))
        inn = max(1, pred_in_counts.get(v, 0))
        base_thr = _edge_thr(G, u, v)
        out_share = EGRESS_LIMITS.get(prov_u, EGRESS_LIMITS.get("aws", 10.0)) / outn
        in_share = INGRESS_LIMITS.get(prov_v, INGRESS_LIMITS.get("aws", 10.0)) / inn
        fe = min(base_thr, out_share, in_share)
        cnt = edge_counts.get((u, v), 0)
        if (u, v) in path_edges:
            cnt += 1
        ratio = cnt / max(fe, 1e-9)
        if ratio > max_ratio:
            max_ratio = ratio
    return max_ratio

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> "BroadCastTopology":
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    if not isinstance(num_partitions, int):
        num_parts = int(num_partitions)
    else:
        num_parts = num_partitions
    if num_parts <= 0:
        return bc_topology

    # Prepare candidate paths for each destination
    K_base = max(6, min(20, num_parts * 2))
    candidates = {}
    costs = {}
    for dst in dsts:
        cands = _get_k_shortest_paths(G, src, dst, K_base)
        if not cands:
            # Fallback: attempt single dijkstra with pure cost
            try:
                p = nx.dijkstra_path(G, src, dst, weight="cost")
                cands = [p]
            except Exception:
                # As last resort, simple unweighted shortest path
                try:
                    p = nx.shortest_path(G, src, dst)
                    cands = [p]
                except Exception:
                    cands = []
        candidates[dst] = cands
        pcosts = []
        for p in cands:
            pcosts.append(_compute_path_cost(G, p))
        costs[dst] = pcosts

    # Global state for approximate time estimation
    edge_counts = {}           # (u,v) -> number of partitions that use this edge
    active_edges = set()       # set of (u,v)
    out_active_counts = {}     # node -> number of active outgoing edges
    in_active_counts = {}      # node -> number of active incoming edges

    # Round-robin assignment of partitions to destinations
    EPS_REL = 0.20
    EPS_ABS = 0.0

    for pid in range(num_parts):
        for dst in dsts:
            cands = candidates.get(dst, [])
            if not cands:
                # Attempt to compute a path now if missing
                try:
                    p = nx.dijkstra_path(G, src, dst, weight="cost")
                    cands = [p]
                    candidates[dst] = cands
                    costs[dst] = [_compute_path_cost(G, p)]
                except Exception:
                    continue

            path_costs = costs.get(dst, [0.0] * len(cands))
            if not path_costs:
                path_costs = [_compute_path_cost(G, p) for p in cands]
                costs[dst] = path_costs

            min_cost = min(path_costs) if path_costs else 0.0
            allowed_idx = []
            for idx, pc in enumerate(path_costs):
                if pc <= min_cost * (1.0 + EPS_REL) + EPS_ABS:
                    allowed_idx.append(idx)
            if not allowed_idx:
                allowed_idx = list(range(len(cands)))

            best_idx = allowed_idx[0]
            best_score = None
            best_time = None
            best_cost = None

            # Evaluate allowed candidates using predicted max ratio
            for idx in allowed_idx:
                p_nodes = cands[idx]
                pred_max_ratio = _predicted_max_ratio_after_add(
                    G, edge_counts, active_edges, out_active_counts, in_active_counts, p_nodes
                )
                pc = path_costs[idx]
                score_tuple = (pred_max_ratio, pc, len(p_nodes))
                if best_score is None or score_tuple < best_score:
                    best_score = score_tuple
                    best_idx = idx
                    best_time = pred_max_ratio
                    best_cost = pc

            chosen_path_nodes = cands[best_idx]
            # Update global state
            for i in range(len(chosen_path_nodes) - 1):
                u = chosen_path_nodes[i]
                v = chosen_path_nodes[i + 1]
                ek = (u, v)
                if ek not in active_edges:
                    active_edges.add(ek)
                    out_active_counts[u] = out_active_counts.get(u, 0) + 1
                    in_active_counts[v] = in_active_counts.get(v, 0) + 1
                edge_counts[ek] = edge_counts.get(ek, 0) + 1

            # Write to topology
            edges = _path_to_edges(G, chosen_path_nodes)
            bc_topology.set_dst_partition_paths(dst, pid, edges)

    return bc_topology


class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {dst: {{str(i): None for i in range(self.num_partitions)}} for dst in dsts}

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
'''
        return {"code": code}
