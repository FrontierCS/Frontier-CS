import json
import os
import networkx as nx
from collections import defaultdict, deque


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        ingress_limits = {"aws": 10, "gcp": 16, "azure": 16}
        egress_limits = {"aws": 5, "gcp": 7, "azure": 16}
        default_data_volume = 300

        try:
            if spec_path and os.path.exists(spec_path):
                with open(spec_path, "r") as f:
                    spec = json.load(f)
                if isinstance(spec, dict):
                    num_vms = int(spec.get("num_vms", num_vms))
                    cfg_files = spec.get("config_files", [])
                    # Try to infer limits and an average data volume from the first config (fallback to defaults)
                    for cfg in cfg_files:
                        try:
                            with open(cfg, "r") as cf:
                                c = json.load(cf)
                            if "ingress_limit" in c:
                                ingress_limits = c["ingress_limit"]
                            if "egress_limit" in c:
                                egress_limits = c["egress_limit"]
                            if "data_vol" in c:
                                default_data_volume = c["data_vol"]
                            # We only need one config to seed defaults
                            break
                        except Exception:
                            continue
        except Exception:
            pass

        code = f'''
import networkx as nx
from collections import defaultdict

NUM_VMS = {num_vms}
INSTANCE_RATE_PER_HOUR = 0.54
INGRESS_LIMITS = {json.dumps(ingress_limits)}
EGRESS_LIMITS = {json.dumps(egress_limits)}
DEFAULT_DATA_VOLUME = {default_data_volume}


class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {{}}
        for dst in dsts:
            self.paths[dst] = {{str(i): None for i in range(self.num_partitions)}}

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


def _provider_of(node: str) -> str:
    if not isinstance(node, str):
        return "aws"
    parts = node.split(":", 1)
    return parts[0].lower() if parts else "aws"


def _k_shortest_paths(G, src, dst, k=6, weight="cost"):
    # Returns up to k simple paths ordered by increasing weight.
    paths = []
    try:
        gen = nx.shortest_simple_paths(G, src, dst, weight=weight)
        for _ in range(k):
            try:
                p = next(gen)
                paths.append(p)
            except StopIteration:
                break
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        pass
    if not paths:
        try:
            p = nx.dijkstra_path(G, src, dst, weight=weight)
            paths = [p]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            paths = []
    return paths


def _edges_from_path(G, path_nodes):
    edges = []
    for i in range(len(path_nodes)-1):
        u = path_nodes[i]
        v = path_nodes[i+1]
        if not G.has_edge(u, v):
            return None
        edges.append((u, v))
    return edges


def _path_cost_and_capacity(G, edges):
    total_cost = 0.0
    min_thr = float("inf")
    for (u, v) in edges:
        d = G[u][v]
        total_cost += float(d.get("cost", 0.0))
        thr = float(d.get("throughput", float("inf")))
        if thr < min_thr:
            min_thr = thr
    return total_cost, min_thr


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Heuristic assignment engine with incremental cost evaluation
    # Constants and initial state
    # Assume an average data volume if not known to weigh costs; evaluator will compute exact cost separately
    s_partition_gb = DEFAULT_DATA_VOLUME / max(1, num_partitions)
    # Rate per second for instances
    rate_per_sec = INSTANCE_RATE_PER_HOUR / 3600.0
    rate_scale = rate_per_sec * NUM_VMS

    # Edge state: counts, effective throughput, time
    edge_partition_count = defaultdict(int)  # (u,v) -> number of partitions routed through this edge
    edge_eff_throughput = {}  # (u,v) -> effective throughput after node limits (Gbps)
    edge_time = {}  # (u,v) -> transfer time in seconds contributed by this edge (for its sum partitions)
    active_edges = set()  # set of (u,v) currently used

    # Node-active edge bookkeeping
    node_out_edges = defaultdict(set)  # u -> set of active outgoing edges (u,v)
    node_in_edges = defaultdict(set)   # v -> set of active incoming edges (u,v)
    node_out_count = defaultdict(int)  # u -> number of active outgoing edges
    node_in_count = defaultdict(int)   # v -> number of active incoming edges

    # Current nodes used in any path
    nodes_used = set()

    # current global max transfer time across edges
    current_max_time = 0.0

    # Precompute K-shortest paths per destination
    K = 6
    dst_candidates = {{}}
    for dst in dsts:
        paths = _k_shortest_paths(G, src, dst, k=K, weight="cost")
        # Filter invalid paths and store edges list with meta
        cand = []
        for p in paths:
            e = _edges_from_path(G, p)
            if e is None or len(e) == 0:
                continue
            total_cost, min_thr = _path_cost_and_capacity(G, e)
            cand.append({{"nodes": p, "edges": e, "cost": total_cost, "min_thr": min_thr}})
        # Fallback to any path via unweighted shortest if needed
        if not cand:
            try:
                p = nx.shortest_path(G, src, dst)
                e = _edges_from_path(G, p)
                if e:
                    total_cost, min_thr = _path_cost_and_capacity(G, e)
                    cand.append({{"nodes": p, "edges": e, "cost": total_cost, "min_thr": min_thr}})
            except Exception:
                pass
        # If still empty, skip (no path); evaluator likely ensures connectivity
        if not cand:
            continue
        dst_candidates[dst] = cand

    # Helper functions
    def eff_share_out(u, out_c):
        prov = _provider_of(u)
        limit = EGRESS_LIMITS.get(prov, 10.0) * NUM_VMS
        # if out_c == 0: no active edge, but in our use it's always >=1 when computing share
        return limit / max(1, out_c)

    def eff_share_in(v, in_c):
        prov = _provider_of(v)
        limit = INGRESS_LIMITS.get(prov, 10.0) * NUM_VMS
        return limit / max(1, in_c)

    def compute_eff_thr(u, v, out_c, in_c):
        cap = float(G[u][v].get("throughput", float("inf")))
        return min(cap, eff_share_out(u, out_c), eff_share_in(v, in_c))

    def evaluate_candidate(path_edges, path_nodes):
        nonlocal current_max_time

        # Determine nodes whose out/in counts would increase (edges newly activated)
        changed_out_nodes = set()
        changed_in_nodes = set()
        for (u, v) in path_edges:
            if (u, v) not in active_edges:
                changed_out_nodes.add(u)
                changed_in_nodes.add(v)

        # Predicted new counts for changed nodes
        # Out/in counts for other nodes remain the same
        out_count_pred = dict((u, node_out_count[u] + (1 if u in changed_out_nodes else 0)) for u in set(list(changed_out_nodes) + list(node_out_count.keys())))
        in_count_pred = dict((v, node_in_count[v] + (1 if v in changed_in_nodes else 0)) for v in set(list(changed_in_nodes) + list(node_in_count.keys())))

        # Build affected edges: all path edges + edges adjacent to changed nodes
        affected_edges = set(path_edges)
        for u in changed_out_nodes:
            affected_edges.update(node_out_edges.get(u, set()))
        for v in changed_in_nodes:
            affected_edges.update(node_in_edges.get(v, set()))

        # Compute new times for affected edges
        s_bits = s_partition_gb * 8.0  # using Gbps, size in Gb per partition
        new_max_time = current_max_time
        for (a, b) in affected_edges:
            # Predicted counts after change
            oc = out_count_pred.get(a, node_out_count[a])
            ic = in_count_pred.get(b, node_in_count[b])
            thr = compute_eff_thr(a, b, oc, ic)
            pcount = edge_partition_count.get((a, b), 0)
            if (a, b) in path_edges:
                pcount += 1
            if pcount > 0 and thr > 0:
                tval = (pcount * s_bits) / thr
            else:
                tval = 0.0
            if tval > new_max_time:
                new_max_time = tval

        # Instance cost incremental (approximate exact delta with current known nodes)
        cur_inst = rate_scale * (len(nodes_used) * current_max_time)
        pred_nodes_used = set(nodes_used)
        pred_nodes_used.update(path_nodes)
        new_inst = rate_scale * (len(pred_nodes_used) * new_max_time)
        delta_inst = new_inst - cur_inst

        # Egress cost incremental for this partition along the path
        path_edge_cost = 0.0
        for (u, v) in path_edges:
            path_edge_cost += float(G[u][v].get("cost", 0.0)) * s_partition_gb

        # Objective is total incremental dollar cost
        objective = delta_inst + path_edge_cost
        return objective, new_max_time, pred_nodes_used, changed_out_nodes, changed_in_nodes

    def commit_path(path_edges, path_nodes, changed_out_nodes, changed_in_nodes, new_max_time):
        nonlocal current_max_time

        # Activate new edges and update counts
        for (u, v) in path_edges:
            previously_active = (u, v) in active_edges
            edge_partition_count[(u, v)] += 1
            if not previously_active:
                active_edges.add((u, v))
                node_out_edges[u].add((u, v))
                node_in_edges[v].add((u, v))

        # Update node out/in counts for changed nodes
        for u in changed_out_nodes:
            node_out_count[u] += 1
        for v in changed_in_nodes:
            node_in_count[v] += 1

        # Update effective throughput and times for affected edges:
        affected_edges = set(path_edges)
        for u in changed_out_nodes:
            affected_edges.update(node_out_edges.get(u, set()))
        for v in changed_in_nodes:
            affected_edges.update(node_in_edges.get(v, set()))

        s_bits = s_partition_gb * 8.0
        for (a, b) in affected_edges:
            oc = node_out_count[a] if (a in node_out_count) else 0
            ic = node_in_count[b] if (b in node_in_count) else 0
            thr = compute_eff_thr(a, b, oc, ic)
            edge_eff_throughput[(a, b)] = thr
            pc = edge_partition_count.get((a, b), 0)
            if pc > 0 and thr > 0:
                edge_time[(a, b)] = (pc * s_bits) / thr
            else:
                edge_time[(a, b)] = 0.0

        # Update nodes used
        for n in path_nodes:
            nodes_used.add(n)

        # Update global max time
        current_max_time = max(current_max_time, new_max_time)

    # Build demand list: round-robin across destinations
    demands = []
    for p in range(num_partitions):
        for d in dsts:
            demands.append((d, p))

    # For each demand, choose best candidate path
    for (dst, part_id) in demands:
        candidates = dst_candidates.get(dst, [])
        if not candidates:
            # No candidate path; attempt to compute one on the fly to avoid failure
            try:
                p = nx.dijkstra_path(G, src, dst, weight="cost")
                e = _edges_from_path(G, p)
                if e:
                    total_cost, min_thr = _path_cost_and_capacity(G, e)
                    candidates = [{{"nodes": p, "edges": e, "cost": total_cost, "min_thr": min_thr}}]
                    dst_candidates[dst] = candidates
                else:
                    continue
            except Exception:
                continue

        best_obj = float("inf")
        best_idx = 0
        best_eval = None

        # Evaluate candidates
        for idx, cand in enumerate(candidates):
            path_nodes = cand["nodes"]
            path_edges = cand["edges"]
            # Quick pruning: if path has zero throughput on any edge, skip
            skip = False
            for (u, v) in path_edges:
                if float(G[u][v].get("throughput", 0.0)) <= 0.0:
                    skip = True
                    break
            if skip:
                continue

            obj, new_max_time, pred_nodes_used, changed_out_nodes, changed_in_nodes = evaluate_candidate(path_edges, path_nodes)
            if obj < best_obj:
                best_obj = obj
                best_idx = idx
                best_eval = (new_max_time, pred_nodes_used, changed_out_nodes, changed_in_nodes)

        # Commit the best path
        chosen = candidates[best_idx]
        chosen_edges = chosen["edges"]
        chosen_nodes = chosen["nodes"]
        if best_eval is None:
            # As a fallback, use first candidate without sophisticated eval
            # This should rarely happen
            new_max_time = current_max_time
            changed_out_nodes = set()
            changed_in_nodes = set()
        else:
            new_max_time, _, changed_out_nodes, changed_in_nodes = best_eval

        commit_path(chosen_edges, chosen_nodes, changed_out_nodes, changed_in_nodes, new_max_time)

        # Record in topology object
        path_edges_with_data = []
        for (u, v) in chosen_edges:
            path_edges_with_data.append([u, v, G[u][v]])
        bc_topology.set_dst_partition_paths(dst, part_id, path_edges_with_data)

    return bc_topology
'''
        return {"code": code}
